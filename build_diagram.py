"""Generate swimlane flowchart (SVG + PNG) for the updated due-diligence flow.

The layout mimics the original 4-column swimlane diagram:
    信贷系统 | 智慧尽调移动端（H5） | 智慧尽调PC端 | 智能体平台
"""
from __future__ import annotations

import xml.sax.saxutils as sx

# ---------- Canvas ----------
W = 1680
H = 1380
LANES = [
    ("信贷系统", 0, 300),
    ("智慧尽调移动端（H5）", 300, 540),
    ("智慧尽调PC端", 840, 540),
    ("智能体平台", 1380, 300),
]
HEADER_H = 46
TOP = HEADER_H + 20  # top padding for content

# ---------- Helpers ----------
SVG: list[str] = []

def add(s: str) -> None:
    SVG.append(s)

def rect(x, y, w, h, fill="#FFFFFF", stroke="#333", rx=6, stroke_width=1.2):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

def text(x, y, s, size=13, fill="#222", anchor="middle", weight="normal"):
    lines = s.split("\n")
    line_h = size + 4
    total = line_h * (len(lines) - 1)
    y0 = y - total / 2
    for i, line in enumerate(lines):
        add(f'<text x="{x}" y="{y0 + i*line_h}" font-family="PingFang SC, Microsoft YaHei, sans-serif" '
            f'font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" font-weight="{weight}">{sx.escape(line)}</text>')

def oval(cx, cy, rx, ry, label, fill="#FFFFFF", stroke="#333"):
    add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
    text(cx, cy, label)

def box(cx, cy, w, h, label, fill="#FFFFFF", stroke="#333", size=13, text_fill="#222"):
    rect(cx - w/2, cy - h/2, w, h, fill=fill, stroke=stroke)
    text(cx, cy, label, size=size, fill=text_fill)

def service_box(cx, cy, w, h, label, size=13):
    box(cx, cy, w, h, label, fill="#F6A623", stroke="#B8751A", text_fill="#FFFFFF", size=size)

# ---------- Arrows ----------
ARROW_DEFS = '''
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#333"/>
  </marker>
  <marker id="arrow-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#1f6feb"/>
  </marker>
</defs>
'''

def line(x1, y1, x2, y2, dashed=False, color="#333", label=None, label_pos=0.5, label_offset=-8, marker=True):
    dash = ' stroke-dasharray="5,4"' if dashed else ''
    marker_attr = f' marker-end="url(#arrow{"-blue" if color=="#1f6feb" else ""})"' if marker else ''
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.4"{dash}{marker_attr}/>')
    if label:
        lx = x1 + (x2 - x1) * label_pos
        ly = y1 + (y2 - y1) * label_pos + label_offset
        for i, ln in enumerate(label.split("\n")):
            add(f'<text x="{lx}" y="{ly + i*14}" font-family="PingFang SC, Microsoft YaHei, sans-serif" '
                f'font-size="11" fill="{color}" text-anchor="middle">{sx.escape(ln)}</text>')

def polyline(points, dashed=False, color="#333", label=None, label_xy=None, marker=True):
    dash = ' stroke-dasharray="5,4"' if dashed else ''
    marker_attr = f' marker-end="url(#arrow{"-blue" if color=="#1f6feb" else ""})"' if marker else ''
    pts = " ".join(f"{x},{y}" for x, y in points)
    add(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.4"{dash}{marker_attr}/>')
    if label and label_xy:
        lx, ly = label_xy
        for i, ln in enumerate(label.split("\n")):
            add(f'<text x="{lx}" y="{ly + i*14}" font-family="PingFang SC, Microsoft YaHei, sans-serif" '
                f'font-size="11" fill="{color}" text-anchor="middle">{sx.escape(ln)}</text>')

# ---------- Build ----------
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add(ARROW_DEFS)
add(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#FFFFFF"/>')

# Lane backgrounds + headers
for name, x, w in LANES:
    rect(x, 0, w, H, fill="#FAFAFA", stroke="#666", rx=0, stroke_width=1.2)
    rect(x, 0, w, HEADER_H, fill="#EDEFF2", stroke="#666", rx=0, stroke_width=1.2)
    text(x + w/2, HEADER_H/2, name, size=15, weight="bold")

# Column centers
CX_CREDIT = 0 + 300/2          # 150
CX_MOBILE = 300 + 540/2        # 570
CX_PC     = 840 + 540/2        # 1110
CX_AGENT  = 1380 + 300/2       # 1530

BOX_W = 200
BOX_H = 54
SVC_W = 200
SVC_H = 54

# === Y coordinates per row ===
Y_START = TOP + 20          # 开始圆圈
Y_11    = Y_START + 10      # 1.1 信贷系统发起尽调
Y_12    = Y_START + 70      # 1.2 移动端发起
Y_21    = Y_11 + 60         # 2.1 创建尽调任务 (PC)
Y_22    = Y_12 + 70         # 2.2 创建尽调任务 (mobile) — same row as 风险初筛服务
Y_RISK_SVC = Y_22           # 风险初筛服务 (orange)
Y_31    = Y_RISK_SVC + 80   # 3.1 风险初筛处理(PC)
Y_32    = Y_31              # 3.2 风险初筛处理(mobile)
Y_4     = Y_32 + 70
Y_5     = Y_4 + 70
Y_6M    = Y_5 + 70          # 6. 模板分案 mobile
Y_TPL_SVC = Y_6M            # 模板分案服务
Y_6PC   = Y_TPL_SVC + 80    # 6. 模板分案 PC
Y_7     = Y_6PC + 70        # 7. 调查问卷 mobile
Y_QST_SVC = Y_7             # 模板问卷配置服务
Y_GUIDE = Y_7 + 70          # 引导式问卷
Y_8M    = Y_GUIDE + 70      # 8. 资料采集、质检 mobile
Y_CLS_SVC = Y_8M            # 资料分类识别服务
Y_8PC   = Y_CLS_SVC + 80    # 8. 资料采集 PC (同一行作为agent对齐)
Y_AGENT_CLS = Y_CLS_SVC     # 资料识别智能体 (与服务同行)
Y_9M    = Y_8PC + 70        # 9. 生成报告 mobile
Y_RPT_SVC = Y_9M            # 报告生成服务
Y_AGENT_RPT = Y_RPT_SVC     # 报告生成智能体
Y_9PC   = Y_RPT_SVC + 70    # 9. 生成报告 PC
Y_10    = Y_9PC + 90        # 10. 报告关联 mobile
Y_LINK_SVC = Y_10           # 尽调任务关联服务
Y_CREDIT_API = Y_10         # 信贷系统 被调用接口
Y_END   = Y_10 + 95

# ==== 开始 ====
oval(CX_MOBILE, Y_START, 45, 18, "开始")

# ==== 1.1 信贷系统发起尽调 ====
box(CX_CREDIT, Y_11, BOX_W, BOX_H, "1.1 信贷系统发起尽调")

# ==== 1.2 移动端发起尽调 ====
box(CX_MOBILE, Y_12, BOX_W + 20, BOX_H + 16,
    "1.2 移动端发起尽调\n(录入借款人、关联人)")

# ==== 2.1 创建尽调任务 (PC) ====
box(CX_PC, Y_21, BOX_W, BOX_H, "2.1 创建尽调任务")

# 1.1 -> 2.1 (API接口, crossing mobile lane)
polyline([(CX_CREDIT + BOX_W/2, Y_11), (CX_PC - BOX_W/2, Y_21)],
         label="API接口", label_xy=(CX_MOBILE, Y_11 - 8))

# 开始 -> 1.2
line(CX_MOBILE, Y_START + 18, CX_MOBILE, Y_12 - (BOX_H+16)/2)

# ==== 2.2 创建尽调任务 (mobile) ====
box(CX_MOBILE, Y_22, BOX_W, BOX_H, "2.2 创建尽调任务")
line(CX_MOBILE, Y_12 + (BOX_H+16)/2, CX_MOBILE, Y_22 - BOX_H/2)

# ==== 风险初筛服务 (PC, orange) ====
service_box(CX_PC, Y_RISK_SVC, SVC_W, SVC_H, "风险初筛服务")
# 2.2 -> 风险初筛服务 (后台服务调用, dashed)
polyline([(CX_MOBILE + BOX_W/2, Y_22), (CX_PC - SVC_W/2, Y_RISK_SVC)],
         dashed=True, label="后台服务调用", label_xy=((CX_MOBILE+CX_PC)/2, Y_22 - 8))

# ==== 3.1 风险初筛处理 (PC) ====
box(CX_PC, Y_31, BOX_W, BOX_H + 16,
    "3.1 风险初筛处理\n(录入管控措施)")
line(CX_PC, Y_RISK_SVC + SVC_H/2, CX_PC, Y_31 - (BOX_H+16)/2)

# ==== 3.2 风险初筛处理 (mobile) ====
box(CX_MOBILE, Y_32, BOX_W, BOX_H + 16,
    "3.2 风险初筛处理\n(录入管控措施)")
# 3.1 -> 3.2 (returned to mobile)
polyline([(CX_PC - BOX_W/2, Y_31), (CX_MOBILE + BOX_W/2, Y_32)])

# ==== 4. 现场尽调 ====
box(CX_MOBILE, Y_4, BOX_W, BOX_H, "4. 现场尽调")
line(CX_MOBILE, Y_32 + (BOX_H+16)/2, CX_MOBILE, Y_4 - BOX_H/2)

# ==== 5. 关联人补充 ====
box(CX_MOBILE, Y_5, BOX_W, BOX_H + 12, "5. 关联人补充\n(可选)")
line(CX_MOBILE, Y_4 + BOX_H/2, CX_MOBILE, Y_5 - (BOX_H+12)/2)

# ==== 6. 模板分案 (mobile) ====
box(CX_MOBILE, Y_6M, BOX_W, BOX_H, "6. 模板分案")
line(CX_MOBILE, Y_5 + (BOX_H+12)/2, CX_MOBILE, Y_6M - BOX_H/2)

# ==== 模板分案服务 (PC, orange) ====
service_box(CX_PC, Y_TPL_SVC, SVC_W, SVC_H, "模板分案服务")
polyline([(CX_MOBILE + BOX_W/2, Y_6M), (CX_PC - SVC_W/2, Y_TPL_SVC)],
         dashed=True, label="后端服务调用", label_xy=((CX_MOBILE+CX_PC)/2, Y_6M - 8))

# ==== 6. 模板分案 (PC) ====
box(CX_PC, Y_6PC, BOX_W, BOX_H, "6. 模板分案")
line(CX_PC, Y_TPL_SVC + SVC_H/2, CX_PC, Y_6PC - BOX_H/2)

# ==== 7. 调查问卷 ====
box(CX_MOBILE, Y_7, BOX_W, BOX_H + 16, "7. 调查问卷\n(文字、图片、音频)")
line(CX_MOBILE, Y_6M + BOX_H/2, CX_MOBILE, Y_7 - (BOX_H+16)/2)

# ==== 模板问卷配置服务 (orange) ====
service_box(CX_PC, Y_QST_SVC, SVC_W, SVC_H + 14, "模板问卷配置服务\n(问题、要求)")
polyline([(CX_MOBILE + BOX_W/2, Y_7), (CX_PC - SVC_W/2, Y_QST_SVC)],
         dashed=True, label="后端服务调用", label_xy=((CX_MOBILE+CX_PC)/2, Y_7 - 8))

# ==== 引导式问卷 ====
GUIDE_X = CX_MOBILE + 140
box(GUIDE_X, Y_GUIDE, 140, BOX_H - 8, "引导式问卷")
polyline([(CX_MOBILE + BOX_W/2, Y_7 + 4), (GUIDE_X, Y_7 + 4), (GUIDE_X, Y_GUIDE - (BOX_H-8)/2)])

# ==== 8. 资料采集、质检 mobile ====
box(CX_MOBILE, Y_8M, BOX_W, BOX_H + 20,
    "8. 资料采集、质检\n(上传、分类、质检、识别)")
polyline([(GUIDE_X, Y_GUIDE + (BOX_H-8)/2), (GUIDE_X, Y_8M - 10), (CX_MOBILE + BOX_W/2, Y_8M - 10), (CX_MOBILE + BOX_W/2, Y_8M - (BOX_H+20)/2 + 2)], marker=False)
# also connect 7 -> 8 main line (implicit through 引导式问卷)
polyline([(CX_MOBILE, Y_7 + (BOX_H+16)/2), (CX_MOBILE, Y_8M - (BOX_H+20)/2)])

# ==== 资料分类识别服务 (orange) ====
service_box(CX_PC, Y_CLS_SVC, SVC_W, SVC_H, "资料分类识别服务")
polyline([(CX_MOBILE + BOX_W/2, Y_8M + 10), (CX_PC - SVC_W/2, Y_CLS_SVC + 10)], dashed=True)

# ==== 资料识别智能体 ====
service_box(CX_AGENT, Y_AGENT_CLS, BOX_W - 20, SVC_H, "资料识别智能体")
polyline([(CX_PC + SVC_W/2, Y_CLS_SVC), (CX_AGENT - (BOX_W-20)/2, Y_AGENT_CLS)],
         label="API调用", label_xy=((CX_PC+CX_AGENT)/2, Y_CLS_SVC - 8))

# ==== 8. 资料采集 (PC) ====
box(CX_PC, Y_8PC, BOX_W, BOX_H + 20,
    "8. 资料采集\n(上传、分类、质检、识别)")
line(CX_PC, Y_CLS_SVC + SVC_H/2, CX_PC, Y_8PC - (BOX_H+20)/2)

# ==== 9. 生成报告 mobile ====
box(CX_MOBILE, Y_9M, BOX_W, BOX_H + 12, "9. 生成报告\n(生产、查看PDF)")
line(CX_MOBILE, Y_8M + (BOX_H+20)/2, CX_MOBILE, Y_9M - (BOX_H+12)/2)

# ==== 报告生成服务 (orange) ====
service_box(CX_PC, Y_RPT_SVC, SVC_W, SVC_H, "报告生成服务")
polyline([(CX_MOBILE + BOX_W/2, Y_9M), (CX_PC - SVC_W/2, Y_RPT_SVC)],
         dashed=True, label="后端服务调用", label_xy=((CX_MOBILE+CX_PC)/2, Y_9M - 8))

# ==== 报告生成智能体 ====
service_box(CX_AGENT, Y_AGENT_RPT, BOX_W - 20, SVC_H, "报告生成智能体")
polyline([(CX_PC + SVC_W/2, Y_RPT_SVC), (CX_AGENT - (BOX_W-20)/2, Y_AGENT_RPT)],
         label="API调用", label_xy=((CX_PC+CX_AGENT)/2, Y_RPT_SVC - 8))

# ==== 9. 生成报告 (PC) ====
box(CX_PC, Y_9PC, BOX_W, BOX_H, "9. 生成报告")
line(CX_PC, Y_RPT_SVC + SVC_H/2, CX_PC, Y_9PC - BOX_H/2)

# =======================================================
# ==== NEW: 10. 报告关联 (mobile) + 尽调任务关联服务 ====
# =======================================================
# Make the mobile 10 box taller and service box taller, so there's room
# for two separate side-by-side arrows (request / response).
M10_W = BOX_W + 20
M10_H = BOX_H + 36
SVC10_W = SVC_W + 10
SVC10_H = SVC_H + 36

box(CX_MOBILE, Y_10, M10_W, M10_H,
    "10. 报告关联\n(选择授信业务，\n提交关联)", fill="#E6F4FF", stroke="#1f6feb")
line(CX_MOBILE, Y_9M + (BOX_H+12)/2, CX_MOBILE, Y_10 - M10_H/2)

service_box(CX_PC, Y_LINK_SVC, SVC10_W, SVC10_H, "尽调任务关联服务")

# Credit API box (taller)
CREDIT_W = BOX_W
CREDIT_H = BOX_H + 46
box(CX_CREDIT, Y_CREDIT_API, CREDIT_W, CREDIT_H,
    "授信业务查询接口\n关联结果回写接口\n(被尽调系统调用)",
    fill="#E6F4FF", stroke="#1f6feb")

# Arrow y-levels (top pair = request, bottom pair = response)
y_top = Y_10 - M10_H/2 + 18
y_bot = Y_10 + M10_H/2 - 18

# --- Mobile -> Service (request) ---
polyline([(CX_MOBILE + M10_W/2, y_top), (CX_PC - SVC10_W/2, y_top)],
         dashed=True, color="#1f6feb")
text((CX_MOBILE + CX_PC)/2, y_top - 9,
     "① 查询可关联授信业务 / ③ 提交关联",
     size=11, fill="#1f6feb")

# --- Service -> Mobile (response) ---
polyline([(CX_PC - SVC10_W/2, y_bot), (CX_MOBILE + M10_W/2, y_bot)],
         dashed=True, color="#1f6feb")
text((CX_MOBILE + CX_PC)/2, y_bot + 12,
     "② 返回授信业务列表 / ④ 返回关联结果",
     size=11, fill="#1f6feb")

# --- Service -> Credit (API call out) ---
polyline([(CX_PC - SVC10_W/2, y_top), (CX_CREDIT + CREDIT_W/2, y_top)],
         color="#1f6feb")
text((CX_PC + CX_CREDIT)/2, y_top - 9,
     "API调用（尽调→信贷）",
     size=11, fill="#1f6feb")

# --- Credit -> Service (API response) ---
polyline([(CX_CREDIT + CREDIT_W/2, y_bot), (CX_PC - SVC10_W/2, y_bot)],
         color="#1f6feb")
text((CX_PC + CX_CREDIT)/2, y_bot + 12,
     "返回数据 / 关联结果",
     size=11, fill="#1f6feb")

# ==== 结束 ====
oval(CX_MOBILE, Y_END, 45, 18, "结束")
line(CX_MOBILE, Y_10 + M10_H/2, CX_MOBILE, Y_END - 18)

# ==== Legend ====
LG_X = 30
LG_Y = H - 150
rect(LG_X, LG_Y, 420, 120, fill="#FFFFFF", stroke="#888")
text(LG_X + 210, LG_Y + 18, "图例", size=14, weight="bold")
# sample shapes
rect(LG_X + 20, LG_Y + 36, 40, 22, fill="#FFFFFF", stroke="#333")
text(LG_X + 90, LG_Y + 47, "前端页面/业务节点", anchor="start")
rect(LG_X + 20, LG_Y + 66, 40, 22, fill="#F6A623", stroke="#B8751A")
text(LG_X + 90, LG_Y + 77, "后端/智能体服务", anchor="start")
rect(LG_X + 220, LG_Y + 36, 40, 22, fill="#E6F4FF", stroke="#1f6feb")
text(LG_X + 290, LG_Y + 47, "本次变更的节点", anchor="start", fill="#1f6feb")
line(LG_X + 220, LG_Y + 80, LG_X + 260, LG_Y + 80, dashed=True, marker=False)
text(LG_X + 290, LG_Y + 80, "异步/后台服务调用", anchor="start")

add("</svg>")

svg_str = "\n".join(SVG)
with open("/workspace/flow-diagram.svg", "w", encoding="utf-8") as f:
    f.write(svg_str)
print("SVG written:", len(svg_str), "bytes")
