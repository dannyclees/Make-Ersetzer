"""Google-Doc-Inhalt für eine Anfrage: Frage/Antwort-Tabelle wie bisher."""

from html import escape

from lead import Lead


def render_html(lead: Lead) -> str:
    rows = "\n".join(
        f"<tr><td><b>{i}</b> {escape(q)}</td><td>{escape(a)}</td></tr>"
        for i, (q, a) in enumerate(lead.answers, start=1)
    )
    contact = " · ".join(escape(x) for x in (lead.name, lead.email or "", lead.phone or "") if x)
    return f"""<html><head><meta charset="utf-8"></head><body>
<p>{contact}</p>
<table border="1" cellpadding="6" style="border-collapse:collapse">
{rows}
</table>
</body></html>"""
