/**
 * Rich-text export helpers.
 *
 * Converts stage content (markdown) into an HTML string and writes it to the
 * clipboard as text/html (with a text/plain fallback), so users can paste
 * formatted output into Google Docs / Word / email. Markdown is rendered with
 * the same ReactMarkdown pipeline used on screen (via react-dom/server), so no
 * extra markdown library is needed.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function shortName(model) {
  return model ? model.split('/')[1] || model : model;
}

export function markdownToHtml(md) {
  if (!md) return '';
  return renderToStaticMarkup(<ReactMarkdown>{md}</ReactMarkdown>);
}

// Replace anonymized "Response A/B/C" labels with bold model short-names.
// Shared with Stage2's on-screen display so both stay consistent.
export function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;
  let result = text;
  Object.entries(labelToModel).forEach(([label, model]) => {
    result = result.replace(new RegExp(label, 'g'), `**${shortName(model)}**`);
  });
  return result;
}

export function buildStage1Html(responses) {
  if (!responses || responses.length === 0) return '';
  const sections = responses.map((r) => {
    const heading = r.persona
      ? `${r.persona} (${shortName(r.model)})`
      : shortName(r.model);
    return `<h3>${escapeHtml(heading)}</h3>${markdownToHtml(r.response)}`;
  });
  return `<h2>Stage 1: Individual Responses</h2>${sections.join('\n')}`;
}

export function buildStage2Html(rankings, labelToModel, aggregateRankings) {
  if (!rankings || rankings.length === 0) return '';
  const sections = rankings.map((rank) => {
    const html = markdownToHtml(deAnonymizeText(rank.ranking, labelToModel));
    let extracted = '';
    if (rank.parsed_ranking && rank.parsed_ranking.length > 0) {
      const items = rank.parsed_ranking
        .map((label) => {
          const name = labelToModel && labelToModel[label]
            ? shortName(labelToModel[label])
            : label;
          return `<li>${escapeHtml(name)}</li>`;
        })
        .join('');
      extracted = `<p><strong>Extracted Ranking:</strong></p><ol>${items}</ol>`;
    }
    return `<h3>${escapeHtml(shortName(rank.model))}</h3>${html}${extracted}`;
  });

  let aggregate = '';
  if (aggregateRankings && aggregateRankings.length > 0) {
    const rows = aggregateRankings
      .map((agg, i) =>
        `<li>#${i + 1} ${escapeHtml(shortName(agg.model))} — Avg: ${agg.average_rank.toFixed(2)} (${agg.rankings_count} votes)</li>`
      )
      .join('');
    aggregate = `<h3>Aggregate Rankings (lower is better)</h3><ol>${rows}</ol>`;
  }

  return `<h2>Stage 2: Peer Rankings</h2>${sections.join('\n')}${aggregate}`;
}

export function buildStage3Html(finalResponse) {
  if (!finalResponse) return '';
  return `<h2>Stage 3: Final Council Answer</h2>`
    + `<p><strong>Chairman: ${escapeHtml(shortName(finalResponse.model))}</strong></p>`
    + markdownToHtml(finalResponse.response);
}

// Combined export of every stage present on an assistant message.
export function buildFullAnswerHtml(msg) {
  const parts = [];
  if (msg.stage1) parts.push(buildStage1Html(msg.stage1));
  if (msg.stage2) {
    parts.push(buildStage2Html(
      msg.stage2,
      msg.metadata?.label_to_model,
      msg.metadata?.aggregate_rankings
    ));
  }
  if (msg.stage3) parts.push(buildStage3Html(msg.stage3));
  return parts.join('\n<hr/>\n');
}

function htmlToPlainText(html) {
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  return tmp.textContent || tmp.innerText || '';
}

/**
 * Copy an HTML string to the clipboard as rich text, with a plain-text fallback.
 * Returns true on success.
 */
export async function copyHtmlToClipboard(html) {
  const text = htmlToPlainText(html);
  try {
    if (navigator.clipboard && window.ClipboardItem) {
      const item = new window.ClipboardItem({
        'text/html': new Blob([html], { type: 'text/html' }),
        'text/plain': new Blob([text], { type: 'text/plain' }),
      });
      await navigator.clipboard.write([item]);
      return true;
    }
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    console.error('Copy to clipboard failed:', e);
    return false;
  }
}
