"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
import json
import asyncio
import logging
import os

from . import storage
from .config import PERSONA_MODEL_CHOICES
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings, suggest_personas
from .file_extractor import extract_file as extract_file_content, SUPPORTED_EXTENSIONS
from .logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class AttachmentData(BaseModel):
    """File attachment metadata + extracted text, sent alongside the message content."""
    file_name: str
    extracted_text: str


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    mode: str = "standard"
    personas: Optional[List[Dict[str, Any]]] = None
    mapping_option: Optional[str] = "round_robin"
    # Model for Stage 3 synthesis; None falls back to CHAIRMAN_MODEL
    chairman_model: Optional[str] = None
    attachment: Optional[AttachmentData] = None


class SuggestPersonasRequest(BaseModel):
    """Request to suggest personas for a query."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.post("/api/extract-file")
async def extract_file_endpoint(file: UploadFile = File(...)):
    """Extract text from an uploaded file (txt, docx, pdf, or image)."""
    MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
    ext = (file.filename or '').rsplit('.', 1)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: .{ext}")
    logger.info("extract-file name=%s size=%d", file.filename, len(data))
    result = await extract_file_content(file.filename or '', data, file.content_type or '')
    return {"file_name": file.filename, **result}


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.post("/api/suggest-personas")
async def suggest_personas_endpoint(request: SuggestPersonasRequest):
    """Suggest 3 expert personas for a query."""
    try:
        personas = await suggest_personas(request.content)
        return {"personas": personas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    deleted = storage.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "id": conversation_id}


@app.get("/api/available-models")
async def available_models():
    """List the models a user can pick from for each Persona Council persona, grouped by cost tier."""
    return {"council_models": PERSONA_MODEL_CHOICES}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Build effective_query: typed content + extracted attachment text (if any)
    effective_query = request.content
    if request.attachment:
        effective_query = (
            f"{request.content}\n\n---\n"
            f"[Attached file: {request.attachment.file_name}]\n"
            f"{request.attachment.extracted_text}"
        )

    # Store only the typed query + file name (not the full extracted text)
    storage.add_user_message(
        conversation_id, request.content,
        attachment_name=request.attachment.file_name if request.attachment else None
    )

    # If this is the first message, generate a title from the typed query only
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        effective_query,
        mode=request.mode,
        personas=request.personas,
        mapping_option=request.mapping_option,
        chairman_model=request.chairman_model
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        metadata={
            **metadata,
            "mode": request.mode,
            "personas": request.personas,
            "mapping_option": request.mapping_option
        }
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": {
            **metadata,
            "mode": request.mode,
            "personas": request.personas,
            "mapping_option": request.mapping_option
        }
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Build effective_query: typed content + extracted attachment text (if any)
    effective_query = request.content
    if request.attachment:
        effective_query = (
            f"{request.content}\n\n---\n"
            f"[Attached file: {request.attachment.file_name}]\n"
            f"{request.attachment.extracted_text}"
        )

    logger.info(
        "message stream conversation=%s mode=%s chairman=%s attachment=%s",
        conversation_id, request.mode, request.chairman_model or "default",
        request.attachment.file_name if request.attachment else None
    )

    async def event_generator():
        try:
            # Store only the typed query + file name (not the full extracted text)
            storage.add_user_message(
                conversation_id, request.content,
                attachment_name=request.attachment.file_name if request.attachment else None
            )

            # Start title generation in parallel from typed query only
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_task = asyncio.create_task(stage1_collect_responses(
                effective_query,
                mode=request.mode,
                personas=request.personas,
                mapping_option=request.mapping_option
            ))
            while not stage1_task.done():
                yield ": keep-alive\n\n"
                await asyncio.sleep(2.0)
            stage1_results = await stage1_task
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings. In persona mode, rank with the
            # deduplicated set of models actually used in Stage 1.
            stage2_council_models = None
            if request.mode == "persona":
                stage2_council_models = list(dict.fromkeys(r['model'] for r in stage1_results))

            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_task = asyncio.create_task(stage2_collect_rankings(
                effective_query,
                stage1_results,
                mode=request.mode,
                council_models=stage2_council_models
            ))
            while not stage2_task.done():
                yield ": keep-alive\n\n"
                await asyncio.sleep(2.0)
            stage2_results, label_to_model = await stage2_task
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_task = asyncio.create_task(stage3_synthesize_final(
                effective_query,
                stage1_results,
                stage2_results,
                mode=request.mode,
                chairman_model=request.chairman_model
            ))
            while not stage3_task.done():
                yield ": keep-alive\n\n"
                await asyncio.sleep(2.0)
            stage3_result = await stage3_task
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result,
                metadata={
                    "label_to_model": label_to_model,
                    "aggregate_rankings": aggregate_rankings,
                    "mode": request.mode,
                    "personas": request.personas,
                    "mapping_option": request.mapping_option
                }
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            logger.exception("message stream failed conversation=%s", conversation_id)
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# Serve the production frontend build (frontend/dist), if present. Guarded so
# local dev (where the frontend isn't built) doesn't fail to start.
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")

# When deployed behind a reverse proxy at a sub-path (e.g. nginx serving this
# app under /content/), set DEPLOY_PREFIX so the app natively understands and
# serves everything under that prefix, with no path rewriting needed in nginx.
# Local dev leaves this unset and is unaffected.
# To be tested: only verified locally with curl (incl. simulated
# X-Forwarded-Proto); not yet exercised through the real nginx + tunnel path.
DEPLOY_PREFIX = os.getenv("DEPLOY_PREFIX", "")
asgi_app = app
if DEPLOY_PREFIX:
    root_app = FastAPI()
    root_app.mount(DEPLOY_PREFIX, app)
    asgi_app = root_app


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting LLM Council API on :8001 prefix=%s", DEPLOY_PREFIX or "/")
    uvicorn.run(
        asgi_app,
        host="0.0.0.0",
        port=8001,
        forwarded_allow_ips="*" if DEPLOY_PREFIX else None,
    )
