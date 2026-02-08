/**
 * Advanced markdown parser for agent responses
 * Supports: tables, code blocks, inline code, bold, italic, lists, links, headers
 */

export function parseMarkdown(text: string): string {
  if (!text) return '';

  let html = text;

  // Code blocks (```lang\ncode```)
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
    const language = lang ? `<span class="text-xs text-violet-400/60">${lang}</span>` : '';
    return `<pre class="bg-white/5 rounded-lg p-4 my-3 overflow-x-auto border border-white/10">${language}<code class="text-sm font-mono text-violet-300 block mt-1">${escapeHtml(code.trim())}</code></pre>`;
  });

  // Tables (GitHub-flavored markdown tables)
  html = parseTable(html);

  // Inline code (`code`)
  html = html.replace(/`([^`]+)`/g, '<code class="bg-white/10 px-1.5 py-0.5 rounded text-sm font-mono text-violet-300">$1</code>');

  // Bold (**text** or __text__)
  html = html.replace(/\*\*([^\*]+)\*\*/g, '<strong class="font-semibold text-white">$1</strong>');
  html = html.replace(/__([^_]+)__/g, '<strong class="font-semibold text-white">$1</strong>');

  // Italic (*text* or _text_) - but not in links
  html = html.replace(/(?<!\w)\*([^\*\n]+)\*(?!\w)/g, '<em class="italic text-white/90">$1</em>');
  html = html.replace(/(?<!\w)_([^_\n]+)_(?!\w)/g, '<em class="italic text-white/90">$1</em>');

  // Links [text](url) — sanitise href to block javascript: / data: XSS
  html = html.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, (_match, text, url) => {
    const trimmed = url.trim().toLowerCase();
    if (trimmed.startsWith('javascript:') || trimmed.startsWith('data:') || trimmed.startsWith('vbscript:')) {
      return text; // render as plain text, strip the dangerous link
    }
    return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="text-violet-400 hover:text-violet-300 underline transition-colors">${text}</a>`;
  });

  // Headers (must come before lists to avoid conflicts)
  html = html.replace(/^#### (.+)$/gm, '<h4 class="text-base font-semibold text-white mt-3 mb-2">$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold text-white mt-4 mb-2">$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold text-white mt-4 mb-2">$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-white mt-4 mb-2">$1</h1>');

  // Unordered lists (- item or * item)
  html = html.replace(/^[\-\*]\s+(.+)$/gm, '<li class="ml-4 my-1 text-white/80">• $1</li>');
  html = html.replace(/(<li class="ml-4 my-1 text-white\/80">• .+<\/li>\n?)+/g, '<ul class="my-2 space-y-1">$&</ul>');

  // Ordered lists (1. item)
  html = html.replace(/^\d+\.\s+(.+)$/gm, (match, content) => {
    const number = match.match(/^(\d+)/)?.[1] || '1';
    return `<li class="ml-4 my-1 text-white/80" value="${number}">${number}. ${content}</li>`;
  });
  html = html.replace(/(<li class="ml-4 my-1 text-white\/80" value="\d+">[\s\S]+?<\/li>\n?)+/g, '<ol class="my-2 space-y-1">$&</ol>');

  // Blockquotes (> text)
  html = html.replace(/^>\s+(.+)$/gm, '<blockquote class="border-l-2 border-violet-400/30 pl-4 my-2 text-white/70 italic">$1</blockquote>');

  // Horizontal rules (---, ***, ___)
  html = html.replace(/^(\-\-\-|\*\*\*|\_\_\_)$/gm, '<hr class="border-white/10 my-4"/>');

  // Line breaks (preserve double newlines as paragraphs)
  html = html.replace(/\n\n/g, '</p><p class="my-2">');
  html = `<p class="my-2">${html}</p>`;
  
  // Clean up empty paragraphs
  html = html.replace(/<p class="my-2"><\/p>/g, '');
  
  return html;
}

/**
 * Parse markdown tables into HTML with scroll wrapper
 */
function parseTable(text: string): string {
  // Match table pattern: header row, separator row, data rows
  const tableRegex = /^\|(.+)\|\n\|[\s\-:\|]+\|\n((?:\|.+\|\n?)+)/gm;
  
  return text.replace(tableRegex, (match, headerRow, bodyRows) => {
    // Parse header
    const headers = headerRow.split('|')
      .map((h: string) => h.trim())
      .filter((h: string) => h);
    
    const headerHtml = headers
      .map((h: string) => `<th>${h}</th>`)
      .join('');
    
    // Parse body rows
    const rows = bodyRows.trim().split('\n');
    const bodyHtml = rows
      .map((row: string) => {
        const cells = row.split('|')
          .map((c: string) => c.trim())
          .filter((c: string) => c);
        
        const cellsHtml = cells
          .map((cell: string) => `<td>${cell}</td>`)
          .join('');
        
        return `<tr>${cellsHtml}</tr>`;
      })
      .join('');
    
    // Wrap table in scrollable container
    return `<div class="table-wrapper"><table class="markdown-table"><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`;
  });
}

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}
