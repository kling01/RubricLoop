"""Self-contained, escaped HTML report. No remote scripts, fonts or services."""
from html import escape
import json

_LABELS = {"pass": "PASS", "fail": "FAIL", "not_applicable": "N/A", "error": "ERROR"}


def render_html(report):
    e = lambda v: escape(str(v), quote=True)
    summary = report["summary"]
    cards = ''.join(f'<div class="metric {k}"><span>{_LABELS[k]}</span><strong>{summary[k]}</strong><small>individual checks</small></div>'
                    for k in _LABELS)
    trace_rows = []
    for i, trace in enumerate(report["traces"], 1):
        checks = [c for c in report["checks"] if c["trace_id"] == trace["id"]]
        rows = ''.join(f'<tr><td><span class="pill {c["status"]}">{_LABELS[c["status"]]}</span></td>'
                       f'<td><b>{e(c["evaluator"])}</b><small>{e(c["kind"])}</small></td><td>{e(c["reason"])}</td></tr>' for c in checks)
        messages = (trace.get("root", {}).get("input") or {}).get("messages", []) + (trace.get("root", {}).get("output") or {}).get("messages", [])
        conversation = ''.join(f'<div class="message"><b>{e(m.get("type", "message"))}</b><p>{e(m.get("content", "")) or "<em>Empty message</em>"}</p></div>' for m in messages)
        trace_rows.append(f'<section class="trace"><header><span class="index">{i:02d}</span><h2>{e(trace["id"])}</h2><span class="count">{len(checks)} checks</span></header>'
            f'<div class="scroll"><table><thead><tr><th>Outcome</th><th>Evaluator</th><th>Evidence / reason</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'<details><summary>Inspect conversation &amp; trace</summary>{conversation}<details><summary>Full normalized JSON</summary><pre>{e(json.dumps(trace, ensure_ascii=False, indent=2))}</pre></details></details></section>')
    is_demo = report.get("demo", False)
    note = "Illustrative, hand-authored traces. Code rules executed locally. No model was called." if is_demo else (
        "Code rules executed locally. No model was called." if report["mode"] == "rules_only" else
        "Includes model judgments. Review reasoning against the original trace; model output can be wrong.")
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgentEval · Evaluation report</title><style>
:root{color-scheme:light;--ink:#17233a;--muted:#64748b;--line:#e2e8f0}*{box-sizing:border-box}body{margin:0;background:#f3f6fb;color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.hero{background:#101b31;color:#fff;padding:38px max(24px,calc((100vw - 1120px)/2)) 34px}.brand{font-size:17px;font-weight:750;letter-spacing:.02em}.brand span{color:#90b3ff}.eyebrow{margin-top:30px;font-size:11px;letter-spacing:.18em;color:#9ab4df;font-weight:700}h1{font-size:36px;line-height:1.15;letter-spacing:-1px;margin:12px 0}.subtitle{color:#bdcbe1;max-width:650px;margin-bottom:0}main{max-width:1168px;margin:26px auto;padding:0 24px}.overview{display:flex;align-items:center;justify-content:space-between;gap:12px}.overview p{color:var(--muted);font-size:13px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:16px 0}.metric{background:#fff;border:1px solid var(--line);border-top:3px solid #8494aa;border-radius:10px;padding:16px 20px}.metric span{font-size:11px;letter-spacing:.1em;font-weight:750}.metric strong{display:block;font-size:34px;line-height:1.4}.metric small{color:var(--muted)}.metric.pass{border-top-color:#169d80}.metric.fail{border-top-color:#e27357}.metric.not_applicable{border-top-color:#7b8ba5}.metric.error{border-top-color:#c49326}.note{padding:13px 17px;border:1px solid #d8e3f5;background:#eaf0fa;border-radius:8px;font-size:13px;margin:18px 0 24px}.trace{background:#fff;border:1px solid var(--line);border-radius:11px;margin:16px 0;overflow:hidden}.trace header{padding:18px 20px;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--line)}.index{font-size:12px;color:#8d9ab0}h2{font-size:16px;margin:0;overflow-wrap:anywhere}.count{margin-left:auto;white-space:nowrap;color:var(--muted);font-size:12px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;text-align:left;min-width:620px}th{padding:10px 20px;background:#fafbfd;font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}td{padding:14px 20px;border-top:1px solid #eff2f7;font-size:13px;vertical-align:top;white-space:pre-wrap;overflow-wrap:anywhere}td:first-child{width:110px}td:nth-child(2){width:220px}td small{display:block;color:var(--muted);font-size:11px;margin-top:4px}.pill{display:inline-block;padding:3px 8px;font-size:10px;font-weight:800;border-radius:5px;letter-spacing:.06em}.pill.pass{background:#e0f4ed;color:#08795c}.pill.fail{background:#fdeae4;color:#b5482b}.pill.not_applicable{background:#edf1f7;color:#65738a}.pill.error{background:#fff2d4;color:#956407}details{border-top:1px solid var(--line);padding:13px 20px;font-size:13px}summary{cursor:pointer;color:#46638e;font-weight:600}.message{display:flex;gap:18px;padding:12px 0;border-top:1px solid #eff2f7}.message:first-of-type{margin-top:14px}.message b{min-width:65px;color:var(--muted);font-size:11px;text-transform:uppercase}.message p{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}pre{max-height:360px;overflow:auto;padding:16px;background:#f3f6fb;font-size:11px}.footer{color:var(--muted);font-size:12px;margin:28px 0 42px}.hash{font-family:monospace;font-size:10px;overflow-wrap:anywhere}@media(max-width:650px){.metrics{grid-template-columns:repeat(2,1fr)}h1{font-size:29px}.hero{padding:25px}.overview{align-items:flex-start;flex-direction:column}}
</style></head><body><div class="hero"><div class="brand">Agent<span>Eval</span> <span style="font-size:10px;margin-left:12px;letter-spacing:.14em">TRACE → EVIDENCE</span></div><div class="eyebrow">EVALUATION REPORT / ALPHA</div><h1>Every judgment, open to inspection.</h1><p class="subtitle">Executable checks. Explicit outcomes. Original traces, one click away.</p></div><main>''' + f'''
<div class="overview"><b>{summary['traces']} traces · {summary['checks']} checks</b><p>{e(report['created_at'][:19])} UTC</p></div><div class="metrics">{cards}</div>
<div class="note">{e(note)}<br>N/A means the rule does not apply. Errors are unresolved evaluations. Neither counts as PASS.</div>
{''.join(trace_rows)}<div class="footer">AgentEval · Local, self-contained report · 1 = PASS / 0 = N/A / −1 = FAIL / null = ERROR<br>
Reports include the supplied trace content. Review before sharing.<div class="hash">Configuration SHA-256: {e(report['config_hash'])}</div></div></main></body></html>'''
