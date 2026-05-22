import { renderMarkdown } from './markdown'

const escapeHtml = (value) => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

export const reportDownloadFilename = (reportId, ext) => {
  const safeId = String(reportId || 'report').replace(/[^a-zA-Z0-9_-]/g, '_')
  return `miroshark-${safeId}.${ext}`
}

export const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export const openPrintWindow = (reportId) => {
  const win = window.open('', '_blank')
  if (!win) {
    throw new Error('Popup blocked. Allow popups to export the report as PDF.')
  }

  win.opener = null
  win.document.open()
  win.document.write(`<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>${escapeHtml(reportId || 'MiroShark Report')}</title>
  <style>
    body {
      margin: 40px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      color: #111;
      background: #fff;
    }
    .loading {
      color: #666;
      font-size: 14px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
  </style>
</head>
<body>
  <div class="loading">Preparing report PDF...</div>
</body>
</html>`)
  win.document.close()
  return win
}

export const writeReportPrintDocument = (win, report, reportId) => {
  if (!win) throw new Error('Print window is not available')

  const title = report?.outline?.title || reportId || 'MiroShark Report'
  const markdown = report?.markdown_content || ''
  if (!markdown.trim()) {
    throw new Error('Report content is not ready yet')
  }

  const rendered = renderMarkdown(markdown)
  win.document.open()
  win.document.write(`<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>${escapeHtml(title)}</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: #f5f5f5;
      color: #0a0a0a;
      font-family: Georgia, "Times New Roman", serif;
      line-height: 1.65;
    }
    .report-print-shell {
      max-width: 820px;
      margin: 0 auto;
      padding: 48px 56px 64px;
      background: #fff;
      min-height: 100vh;
    }
    .report-kicker {
      display: inline-block;
      margin-bottom: 22px;
      padding: 6px 10px;
      background: #0a0a0a;
      color: #fff;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.22em;
      text-transform: uppercase;
    }
    .report-id {
      margin-left: 12px;
      color: #777;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 11px;
    }
    .report-body h1,
    .report-body .md-h2 {
      margin: 0 0 18px;
      font-size: 34px;
      line-height: 1.16;
    }
    .report-body .md-h3 {
      margin: 30px 0 12px;
      font-size: 24px;
      line-height: 1.25;
      break-after: avoid;
    }
    .report-body .md-h4 {
      margin: 22px 0 8px;
      font-size: 18px;
      break-after: avoid;
    }
    .report-body .md-p {
      margin: 0 0 14px;
      font-size: 14px;
    }
    .report-body .md-quote {
      margin: 0 0 20px;
      padding-left: 18px;
      border-left: 3px solid #d4d4d4;
      color: #555;
      font-style: italic;
    }
    .report-body .md-ul,
    .report-body .md-ol {
      margin: 0 0 16px;
      padding-left: 24px;
    }
    .report-body .md-li,
    .report-body .md-oli {
      margin: 5px 0;
      font-size: 14px;
    }
    .report-body .code-block {
      white-space: pre-wrap;
      padding: 12px;
      border: 1px solid #ddd;
      background: #f7f7f7;
      font-size: 12px;
    }
    @media print {
      @page { margin: 0.65in; }
      body { background: #fff; }
      .report-print-shell {
        max-width: none;
        min-height: auto;
        padding: 0;
      }
      .report-body .md-h3,
      .report-body .md-h4 {
        page-break-after: avoid;
      }
    }
  </style>
</head>
<body>
  <main class="report-print-shell">
    <div>
      <span class="report-kicker">Prediction Report</span>
      <span class="report-id">${escapeHtml(reportId || '')}</span>
    </div>
    <article class="report-body">${rendered}</article>
  </main>
  <script>
    window.addEventListener('load', () => {
      setTimeout(() => {
        window.focus();
        window.print();
      }, 250);
    });
  </script>
</body>
</html>`)
  win.document.close()
}
