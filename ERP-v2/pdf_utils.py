"""
PDF 共用模組 — COSH 電腦舖 ERP
溫馨文青風格：柔和色調、圓角感、簡約留白
混合字型：CJK TTF (CJK) + Helvetica (Latin/數字)
"""
import io
import os
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, KeepTogether
)

# ── 字型註冊 ────────────────────────────────────
CJK_FONT = 'CJK'
LATIN_FONT = 'Helvetica'
LATIN_FONT_B = 'Helvetica-Bold'
_font_registered = False

_CJK_FONT_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansTC-Regular.ttf'),
    'C:/Windows/Fonts/msjh.ttc',
    'C:/Windows/Fonts/mingliu.ttc',
    'C:/Windows/Fonts/kaiu.ttf',
    'C:/Windows/Fonts/simsun.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/PingFang.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
    '/System/Library/Fonts/Supplemental/Songti.ttc',
    '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJKtc-Regular.ttf',
]

def _find_cjk_font():
    for path in _CJK_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None

def _ensure_font():
    global _font_registered, CJK_FONT
    if _font_registered:
        return
    font_path = _find_cjk_font()
    if font_path:
        if font_path.endswith('.ttc'):
            pdfmetrics.registerFont(TTFont(CJK_FONT, font_path, subfontIndex=0))
        else:
            pdfmetrics.registerFont(TTFont(CJK_FONT, font_path))
        _font_registered = True
    else:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        CJK_FONT = 'STSong-Light'
        _font_registered = True


def _is_ttf_font():
    return CJK_FONT == 'CJK'


def T(text):
    """混合字型：CJK 字元用 CJK font，其餘用 Helvetica"""
    if not text:
        return ''
    text = str(text)
    if not _is_ttf_font():
        return xml_escape(text)
    parts, buf, is_cjk = [], '', None
    for ch in text:
        ch_cjk = ord(ch) >= 0x2E80
        if is_cjk is not None and ch_cjk != is_cjk:
            if is_cjk:
                parts.append(xml_escape(buf))
            else:
                parts.append(f'<font face="{LATIN_FONT}">{xml_escape(buf)}</font>')
            buf = ''
        buf += ch
        is_cjk = ch_cjk
    if buf:
        if is_cjk:
            parts.append(xml_escape(buf))
        else:
            parts.append(f'<font face="{LATIN_FONT}">{xml_escape(buf)}</font>')
    return ''.join(parts)


def Tb(text):
    """混合字型 + 粗體"""
    if not text:
        return ''
    text = str(text)
    if not _is_ttf_font():
        return f'<b>{xml_escape(text)}</b>'
    parts, buf, is_cjk = [], '', None
    for ch in text:
        ch_cjk = ord(ch) >= 0x2E80
        if is_cjk is not None and ch_cjk != is_cjk:
            if is_cjk:
                parts.append(f'<b>{xml_escape(buf)}</b>')
            else:
                parts.append(f'<font face="{LATIN_FONT_B}"><b>{xml_escape(buf)}</b></font>')
            buf = ''
        buf += ch
        is_cjk = ch_cjk
    if buf:
        if is_cjk:
            parts.append(f'<b>{xml_escape(buf)}</b>')
        else:
            parts.append(f'<font face="{LATIN_FONT_B}"><b>{xml_escape(buf)}</b></font>')
    return ''.join(parts)


# ── 文青色彩 ──────────────────────────────────
C_WARM    = colors.HexColor('#5a3e28')   # 暖棕主色（標題、強調文字）
C_LATTE   = colors.HexColor('#d4c5b2')   # 拿鐵色分隔線
C_CREAM   = colors.HexColor('#faf6f0')   # 奶油底色（表格交替行）
C_SAND    = colors.HexColor('#f0e8dc')   # 沙色（表頭底色）
C_TEXT    = colors.HexColor('#3d3229')   # 正文深色
C_SUB     = colors.HexColor('#9a8b78')   # 次要文字（日期、備註）
C_LINE    = colors.HexColor('#e0d6c8')   # 淡線條
C_ACCENT  = colors.HexColor('#c8956c')   # 焦糖橘（金額強調）
C_WHITE   = colors.white

# ── 公司資訊 ────────────────────────────────────
COMPANIES = {
    '電瑙舖資訊有限公司': {'tax_id': '27488187'},
    '鋒鑫資訊有限公司':  {'tax_id': '90284112'},
}
DEFAULT_COMPANY = '電瑙舖資訊有限公司'
BRAND = 'COSH 電腦舖'
BRAND_REGION = '台中豐原 · 潭子 · 大雅'


# ── 樣式 ──────────────────────────────────────
def _styles():
    _ensure_font()
    return {
        'brand': ParagraphStyle('brand', fontName=CJK_FONT, fontSize=15,
                                leading=20, textColor=C_WARM, alignment=0,
                                spaceAfter=1 * mm),
        'subtitle': ParagraphStyle('subtitle', fontName=CJK_FONT, fontSize=8,
                                   leading=11, textColor=C_SUB, alignment=0),
        'date_right': ParagraphStyle('date_right', fontName=CJK_FONT, fontSize=9,
                                     leading=13, textColor=C_SUB, alignment=2),
        'greeting': ParagraphStyle('greeting', fontName=CJK_FONT, fontSize=10,
                                   leading=15, textColor=C_TEXT,
                                   spaceBefore=4 * mm, spaceAfter=2 * mm),
        'body': ParagraphStyle('body', fontName=CJK_FONT, fontSize=9.5,
                               leading=14, textColor=C_TEXT,
                               spaceAfter=2 * mm),
        'doc_type': ParagraphStyle('doc_type', fontName=CJK_FONT, fontSize=9,
                                   leading=13, textColor=C_SUB, alignment=0),
        'label': ParagraphStyle('label', fontName=CJK_FONT, fontSize=8,
                                leading=11, textColor=C_SUB),
        'value': ParagraphStyle('value', fontName=CJK_FONT, fontSize=9,
                                leading=12, textColor=C_TEXT),
        'normal': ParagraphStyle('normal', fontName=CJK_FONT, fontSize=9,
                                 leading=12, textColor=C_TEXT),
        'small': ParagraphStyle('small', fontName=CJK_FONT, fontSize=7.5,
                                leading=10, textColor=C_SUB),
        'cell': ParagraphStyle('cell', fontName=CJK_FONT, fontSize=8.5,
                               leading=11, textColor=C_TEXT),
        'cell_r': ParagraphStyle('cell_r', fontName=CJK_FONT, fontSize=8.5,
                                 leading=11, textColor=C_TEXT, alignment=2),
        'cell_c': ParagraphStyle('cell_c', fontName=CJK_FONT, fontSize=8.5,
                                 leading=11, textColor=C_TEXT, alignment=1),
        'hdr': ParagraphStyle('hdr', fontName=CJK_FONT, fontSize=8,
                              leading=11, textColor=C_WARM, alignment=1),
        'total_label': ParagraphStyle('total_label', fontName=CJK_FONT, fontSize=9,
                                      leading=12, textColor=C_SUB, alignment=2),
        'total_val': ParagraphStyle('total_val', fontName=CJK_FONT, fontSize=10,
                                    leading=13, textColor=C_WARM, alignment=2),
        'closing': ParagraphStyle('closing', fontName=CJK_FONT, fontSize=9.5,
                                  leading=14, textColor=C_TEXT,
                                  spaceBefore=5 * mm),
        'sign_name': ParagraphStyle('sign_name', fontName=CJK_FONT, fontSize=9.5,
                                    leading=13, textColor=C_WARM),
        'sign_title': ParagraphStyle('sign_title', fontName=CJK_FONT, fontSize=8,
                                     leading=11, textColor=C_SUB),
        'footer': ParagraphStyle('footer', fontName=CJK_FONT, fontSize=7,
                                 leading=9, textColor=C_SUB, alignment=1),
        'thanks': ParagraphStyle('thanks', fontName=CJK_FONT, fontSize=9,
                                 leading=13, textColor=C_SUB, alignment=1,
                                 spaceBefore=6 * mm),
    }


def fmt_num(n):
    if n is None:
        return ''
    try:
        n = int(round(float(n)))
        return f'{n:,}'
    except (ValueError, TypeError):
        return str(n)


def fmt_date(d):
    if not d:
        return ''
    return str(d).strip()[:10]


# ── 書信式表頭 ──────────────────────────────────
def build_header(doc_type_label, doc_no, company=None, extra_fields=None,
                 customer_name='', salesperson=''):
    """
    書信式版面：
    左上 品牌 letterhead → 日期靠右 → 收件人問候 →
    正文引言（含單號、發票等資訊）→ 品項表格
    """
    S = _styles()
    company = company or DEFAULT_COMPANY
    tax_id = COMPANIES.get(company, {}).get('tax_id', '')
    elements = []

    # ── Letterhead：品牌左上 ──
    elements.append(Paragraph(T(BRAND), S['brand']))
    co_line = f'{company}　{BRAND_REGION}'
    if tax_id:
        co_line += f'　統編 {tax_id}'
    elements.append(Paragraph(T(co_line), S['subtitle']))
    elements.append(Spacer(1, 3 * mm))
    elements.append(HRFlowable(width='100%', thickness=0.5,
                               color=C_LATTE, spaceAfter=4 * mm))

    # ── 日期靠右 ──
    date_val = ''
    invoice_val = ''
    remaining_fields = []
    if extra_fields:
        for label, value in extra_fields:
            if label in ('日期', '報價日期', '訂單日期'):
                date_val = str(value)
            elif label in ('發票號碼',):
                invoice_val = str(value)
            elif label not in ('業務', '客戶'):
                remaining_fields.append((label, value))

    if date_val:
        elements.append(Paragraph(T(date_val), S['date_right']))
    elements.append(Spacer(1, 3 * mm))

    # ── 收件人問候 ──
    cust = customer_name or ''
    if cust:
        elements.append(Paragraph(T(f'{cust}　您好：'), S['greeting']))
    else:
        elements.append(Paragraph(T('您好：'), S['greeting']))

    # ── 正文開場：用一段文字帶出單號、發票等資訊 ──
    type_map = {'銷貨單': '銷貨', '報價單': '報價', '訂購單': '訂購'}
    action = type_map.get(doc_type_label, doc_type_label.replace('單', ''))
    body_parts = [f'以下為您的{action}明細']
    if doc_no:
        body_parts.append(f'單號 {doc_no}')
    if invoice_val:
        body_parts.append(f'發票號碼 {invoice_val}')
    body_text = '，'.join(body_parts) + '：'
    elements.append(Paragraph(T(body_text), S['body']))

    # ── 其餘欄位（如有）簡單列出 ──
    if remaining_fields:
        for label, value in remaining_fields:
            if value:
                elements.append(Paragraph(
                    T(f'{label}：{value}'), S['small']))
        elements.append(Spacer(1, 2 * mm))

    return elements


# ── 品項表格（溫馨風） ──────────────────────────
def build_items_table(headers, rows, col_widths=None, align_right_cols=None):
    S = _styles()
    align_right_cols = align_right_cols or set()

    # 表頭 — 沙色底、暖棕文字、不用深色反白
    hdr_cells = [Paragraph(T(h), S['hdr']) for h in headers]
    data = [hdr_cells]

    for row in rows:
        cells = []
        for ci, v in enumerate(row):
            if isinstance(v, Paragraph):
                cells.append(v)
            else:
                style = S['cell_r'] if ci in align_right_cols else S['cell']
                cells.append(Paragraph(T(str(v)), style))
        data.append(cells)

    n_cols = len(headers)
    if col_widths:
        cw = [w * mm for w in col_widths]
    else:
        avail = A4[0] - 40 * mm
        cw = [avail / n_cols] * n_cols

    tbl = Table(data, colWidths=cw, repeatRows=1)
    style_cmds = [
        # 表頭：沙色底 + 暖棕字
        ('BACKGROUND', (0, 0), (-1, 0), C_SAND),
        ('TEXTCOLOR', (0, 0), (-1, 0), C_WARM),
        ('FONTNAME', (0, 0), (-1, -1), CJK_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        # 只有水平線、不用 GRID（輕盈感）
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, C_LATTE),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, C_LATTE),
    ]
    # 交替行底色 — 非常淡的奶油色
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), C_CREAM))
        # 每行底部淡線
        if i < len(data) - 1:
            style_cmds.append(('LINEBELOW', (0, i), (-1, i), 0.3, C_LINE))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl


# ── 合計區塊 ──────────────────────────────────
def build_totals_block(lines):
    S = _styles()
    data = []
    for idx, (label, val) in enumerate(lines):
        # 最後一行（通常是合計或尾款）用強調色
        if idx == len(lines) - 1 or label == '合計':
            data.append([
                Paragraph(Tb(label), S['total_label']),
                Paragraph(Tb(f'NT$ {val}'), S['total_val']),
            ])
        else:
            data.append([
                Paragraph(T(label), S['total_label']),
                Paragraph(T(f'NT$ {val}'), S['cell_r']),
            ])
    tbl = Table(data, colWidths=[35 * mm, 40 * mm], hAlign='RIGHT')
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), CJK_FONT),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 0), (-1, 0), 0.6, C_LATTE),
    ]))
    return tbl


# ── 備註 ──────────────────────────────────────
def build_note_block(note):
    if not note:
        return Spacer(1, 0)
    S = _styles()
    return KeepTogether([
        Paragraph(T('備註'), S['label']),
        Spacer(1, 1.5 * mm),
        Paragraph(T(note), S['small']),
    ])


# ── 書信結尾：感謝 + 署名 + 簽收 ──────────────────
def build_signature_block(labels=None, salesperson=''):
    """
    書信式結尾（客戶文件）：感謝語 → 署名 → 簽收欄
    若 labels 含多個值（如 ['主管','盤點人']），改用內部文件格式
    """
    S = _styles()
    elements = []

    # 內部文件（多簽名欄）：直接畫簽名格
    if labels and len(labels) > 1:
        elements.append(Spacer(1, 8 * mm))
        sig_line = '＿＿＿＿＿＿＿＿＿＿＿'
        row = [Paragraph(T(f'{lb}　{sig_line}'), S['value']) for lb in labels]
        col_w = [(A4[0] - 44 * mm) / len(labels)] * len(labels)
        tbl = Table([row], colWidths=col_w)
        tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), CJK_FONT),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(tbl)
        return elements

    # 客戶文件：書信式結尾
    elements.append(Paragraph(
        T('如有任何問題，歡迎隨時與我們聯繫。'), S['closing']))
    elements.append(Paragraph(
        T('感謝您的支持與信賴！'), S['closing']))
    elements.append(Spacer(1, 5 * mm))

    # 署名
    elements.append(Paragraph(Tb(BRAND), S['sign_name']))
    if salesperson:
        elements.append(Paragraph(T(f'經辦人：{salesperson}'), S['sign_title']))
    elements.append(Spacer(1, 8 * mm))

    # 簽收欄 — 簡單一行
    sig_line = '＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿'
    data = [[
        Paragraph(T(f'簽收　{sig_line}'), S['value']),
        Paragraph(T(f'日期　{sig_line}'), S['value']),
    ]]
    col_w = [(A4[0] - 44 * mm) / 2] * 2
    tbl = Table(data, colWidths=col_w)
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), CJK_FONT),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(tbl)
    return elements


# ── 頁尾 ────────────────────────────────────
def build_footer_elements():
    S = _styles()
    return [
        Spacer(1, 8 * mm),
        HRFlowable(width='30%', thickness=0.3, color=C_LATTE,
                   spaceAfter=2 * mm, hAlign='CENTER'),
        Paragraph(T(f'{BRAND}　{BRAND_REGION}'), S['footer']),
    ]


# ── 主入口 ────────────────────────────────────
def generate_pdf(elements_fn):
    _ensure_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    elements = elements_fn()
    doc.build(elements)
    buf.seek(0)
    return buf
