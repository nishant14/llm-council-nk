import { useState } from 'react';
import { copyHtmlToClipboard } from '../utils/exportRichText';

/**
 * Small "copy as rich text" button with a transient "Copied ✓" confirmation.
 * `getHtml` is called on click and must return the HTML string to copy.
 */
export default function CopyButton({ getHtml, label = 'Copy', className = '' }) {
  const [copied, setCopied] = useState(false);

  const handleClick = async () => {
    const ok = await copyHtmlToClipboard(getHtml());
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <button
      type="button"
      className={`copy-btn ${className}`}
      onClick={handleClick}
      title="Copy as rich text (paste into Docs, Word, email)"
    >
      {copied ? 'Copied ✓' : `⧉ ${label}`}
    </button>
  );
}
