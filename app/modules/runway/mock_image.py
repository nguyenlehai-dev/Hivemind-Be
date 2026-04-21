from urllib.parse import quote


def build_mock_result_image(prompt: str, model_id: str) -> str:
    safe_prompt = prompt[:80] or "Untitled scene"
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='1280' height='720'>
      <defs>
        <linearGradient id='bg' x1='0%' y1='0%' x2='100%' y2='100%'>
          <stop offset='0%' stop-color='#102038'/>
          <stop offset='100%' stop-color='#245dff'/>
        </linearGradient>
      </defs>
      <rect width='1280' height='720' fill='url(#bg)'/>
      <circle cx='1040' cy='120' r='180' fill='rgba(255,255,255,0.08)'/>
      <text x='80' y='170' fill='white' font-size='42' font-family='Arial'>Runway Custom Workflow</text>
      <text x='80' y='250' fill='white' font-size='28' font-family='Arial'>{model_id}</text>
      <foreignObject x='80' y='310' width='1020' height='220'>
        <div xmlns='http://www.w3.org/1999/xhtml'
             style='font-size:36px;color:white;font-family:Arial;line-height:1.3;'>
          {safe_prompt}
        </div>
      </foreignObject>
    </svg>
    """.strip()
    return f"data:image/svg+xml;utf8,{quote(svg)}"
