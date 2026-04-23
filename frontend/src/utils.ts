import type { DocStatus, Flowcard } from './types';

export function statusLabel(status: DocStatus): string {
  if (status === 'ok') {
    return '可用';
  }
  if (status === 'creating') {
    return '处理中';
  }
  return '失败';
}

export function statusTone(status: DocStatus): string {
  if (status === 'ok') {
    return 'success';
  }
  if (status === 'creating') {
    return 'warning';
  }
  return 'danger';
}

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function multiline(value: string | undefined): string {
  return escapeHtml(value || '').replace(/\n/g, '<br />');
}

export function validateRag(k: number, rerankingEnabled: boolean, rerankingK: number): string | null {
  if (!Number.isInteger(k) || k < 1) {
    return 'k 必须为大于 0 的整数';
  }
  if (rerankingEnabled && (!Number.isInteger(rerankingK) || rerankingK < k)) {
    return 'reranking_k 必须大于或等于 k';
  }
  return null;
}

export function openFlowcardTable(flowcardId: string, flowcard: Flowcard): void {
  const rows = flowcard.jobs
    .map(
      (job, index) => `
        <tr>
          <td class="index">${index + 1}</td>
          <td>${multiline(job.name)}</td>
          <td>${multiline(job.requirement)}</td>
          <td>${multiline(job.start_and_end_time)}</td>
          <td>${multiline(job.result)}</td>
          <td>${multiline(job.operator)}</td>
          <td>${multiline(job.note)}</td>
        </tr>`
    )
    .join('');

  const generatedAt = new Date().toLocaleString('zh-CN');
  const title = flowcard.title || '芯片测试流程卡';
  const html = `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHtml(title)}</title>
    <style>
      :root {
        color: #172033;
        font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
      }
      body {
        margin: 0;
        background: #f6f8fb;
      }
      main {
        max-width: 1180px;
        margin: 0 auto;
        padding: 28px;
      }
      header {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 18px;
      }
      h1 {
        margin: 0 0 8px;
        font-size: 28px;
        font-weight: 760;
      }
      .meta {
        color: #5b667a;
        font-size: 13px;
        line-height: 1.7;
      }
      button {
        border: 1px solid #1d4ed8;
        border-radius: 6px;
        background: #2563eb;
        color: #fff;
        cursor: pointer;
        font-size: 14px;
        padding: 9px 14px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        background: #fff;
        border: 1px solid #ccd5e3;
      }
      th,
      td {
        border: 1px solid #ccd5e3;
        padding: 11px 12px;
        text-align: left;
        vertical-align: top;
        line-height: 1.55;
      }
      th {
        background: #eaf1fb;
        color: #1f3658;
        font-weight: 700;
      }
      td.index {
        width: 56px;
        text-align: center;
      }
      @media print {
        body {
          background: #fff;
        }
        main {
          max-width: none;
          padding: 0;
        }
        .print-actions {
          display: none;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <header>
        <div>
          <h1>${escapeHtml(title)}</h1>
          <div class="meta">流程卡 ID：${escapeHtml(flowcardId)}</div>
          <div class="meta">打开时间：${escapeHtml(generatedAt)}</div>
        </div>
        <div class="print-actions">
          <button onclick="window.print()">打印</button>
        </div>
      </header>
      <table>
        <thead>
          <tr>
            <th>序号</th>
            <th>工序</th>
            <th>条件要求</th>
            <th>作业起止时间</th>
            <th>作业结果</th>
            <th>作业员</th>
            <th>备注</th>
          </tr>
        </thead>
        <tbody>
          ${rows || '<tr><td colspan="7">暂无工序</td></tr>'}
        </tbody>
      </table>
    </main>
  </body>
</html>`;

  const target = window.open('', '_blank');
  if (!target) {
    throw new Error('浏览器阻止了新标签页');
  }

  target.document.open();
  target.document.write(html);
  target.document.close();
}
