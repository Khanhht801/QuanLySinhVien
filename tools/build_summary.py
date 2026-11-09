"""Rebuild only the semester summary tab; preserve the rest of main.ui."""
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def prop(el, name, value, kind='string'):
    for old in list(el.findall(f'property[@name="{name}"]')):
        el.remove(old)
    p = ET.SubElement(el, 'property', name=name)
    node = ET.SubElement(p, kind)
    if isinstance(value, dict):
        for key, val in value.items():
            ET.SubElement(node, key).text = str(val)
    else:
        node.text = str(value)


def size(el, name, width, height):
    prop(el, name, {'width': width, 'height': height}, 'size')


def font(el, points=9, bold=False):
    p = ET.SubElement(el, 'property', name='font')
    f = ET.SubElement(p, 'font')
    ET.SubElement(f, 'family').text = 'Segoe UI'
    ET.SubElement(f, 'pointsize').text = str(points)
    ET.SubElement(f, 'bold').text = str(bold).lower()


def widget(kind, name):
    return ET.Element('widget', {'class': kind, 'name': name})


def layout(parent, kind, name, margin=0, spacing=8):
    result = ET.SubElement(parent, 'layout', {'class': kind, 'name': name})
    for edge in ['left', 'top', 'right', 'bottom']:
        prop(result, edge + 'Margin', margin, 'number')
    prop(result, 'spacing', spacing, 'number')
    return result


def add(parent, child, **position):
    ET.SubElement(parent, 'item', position).append(child)
    return child


def label(name, text='', points=9, bold=False):
    result = widget('QLabel', name)
    prop(result, 'text', text)
    font(result, points, bold)
    return result


def image(name, asset, width=20, height=20):
    result = label(name)
    prop(result, 'pixmap', f':/icons/{asset}.svg', 'pixmap')
    prop(result, 'scaledContents', 'true', 'bool')
    size(result, 'minimumSize', width, height)
    size(result, 'maximumSize', width, height)
    return result


def button(name, text, asset, height=38, icon_size=24):
    result = widget('QPushButton', name)
    prop(result, 'text', text)
    font(result, 10, True)
    icon = ET.SubElement(ET.SubElement(result, 'property', name='icon'), 'iconset', resource='resources.qrc')
    ET.SubElement(icon, 'normaloff').text = f':/icons/{asset}.svg'
    size(result, 'iconSize', icon_size, icon_size)
    size(result, 'minimumSize', 0, height)
    prop(result, 'cursor', 'PointingHandCursor', 'cursorShape')
    return result


def spacer(parent, name):
    s = ET.SubElement(ET.SubElement(parent, 'item'), 'spacer', name=name)
    prop(s, 'orientation', 'Qt::Vertical', 'enum')
    size(s, 'sizeHint', 10, 8)


def brush(item, name, rgb):
    p = ET.SubElement(item, 'property', name=name)
    b = ET.SubElement(p, 'brush', brushstyle='SolidPattern')
    color = ET.SubElement(b, 'color', alpha='255')
    for channel, start in [('red', 0), ('green', 2), ('blue', 4)]:
        ET.SubElement(color, channel).text = str(int(rgb[start:start + 2], 16))


def table(name, headings, rows):
    result = widget('QTableWidget', name)
    font(result)
    prop(result, 'rowCount', len(rows), 'number')
    prop(result, 'columnCount', len(headings), 'number')
    prop(result, 'editTriggers', 'QAbstractItemView::NoEditTriggers', 'set')
    prop(result, 'selectionBehavior', 'QAbstractItemView::SelectRows', 'enum')
    prop(result, 'selectionMode', 'QAbstractItemView::SingleSelection', 'enum')
    prop(result, 'alternatingRowColors', 'true', 'bool')
    prop(result, 'sortingEnabled', 'false', 'bool')
    for name_, value, kind in [
        ('verticalHeaderVisible', 'false', 'bool'),
        ('verticalHeaderDefaultSectionSize', '26', 'number'),
        ('horizontalHeaderDefaultSectionSize', '105', 'number'),
        ('horizontalHeaderStretchLastSection', 'true', 'bool'),
    ]:
        ET.SubElement(ET.SubElement(result, 'attribute', name=name_), kind).text = value
    for _ in rows:
        ET.SubElement(result, 'row')
    for title in headings:
        prop(ET.SubElement(result, 'column'), 'text', title)
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            item = ET.SubElement(result, 'item', row=str(row), column=str(column))
            prop(item, 'text', value)
            left = (name == 'summaryTable' and column == 2) or (name == 'subjectsTable' and column == 1 and row < 3)
            prop(item, 'textAlignment', 'AlignLeft|AlignVCenter' if left else 'AlignCenter', 'set')
            font(item, 9, (name == 'summaryTable' and column >= 6) or (name == 'subjectsTable' and row == 3))
            if name == 'summaryTable' and column >= 6:
                brush(item, 'background', ['dffbd5', 'fff5cd', 'dffbd5', 'ffdcd8', 'dffbd5'][row])
                if column == 7:
                    brush(item, 'foreground', 'c51d1d' if row == 3 else '087d20')
            if name == 'subjectsTable' and row == 3:
                brush(item, 'background', 'd9facb')
    return result


def build():
    path = ROOT / 'main.ui'
    tree = ET.parse(path)
    ui = tree.getroot()
    page = ui.find('.//widget[@name="summaryTab"]')
    for old in list(page.findall('layout')):
        page.remove(old)

    outer = layout(page, 'QVBoxLayout', 'summaryPageLayout')
    scroll = add(outer, widget('QScrollArea', 'summaryScroll'))
    prop(scroll, 'frameShape', 'QFrame::NoFrame', 'enum')
    prop(scroll, 'widgetResizable', 'true', 'bool')
    prop(scroll, 'horizontalScrollBarPolicy', 'Qt::ScrollBarAlwaysOff', 'enum')
    content = widget('QWidget', 'summaryContent')
    scroll.append(content)
    content_layout = layout(content, 'QVBoxLayout', 'summaryContentLayout', 12, 12)
    content_layout.set('stretch', '3,2')

    card = add(content_layout, widget('QFrame', 'summaryGradesCard'))
    card_layout = layout(card, 'QVBoxLayout', 'summaryGradesLayout', 0, 0)
    toolbar = add(card_layout, widget('QFrame', 'summaryToolbar'))
    toolbar_layout = layout(toolbar, 'QHBoxLayout', 'summaryToolbarLayout', 5, 8)
    add(toolbar_layout, image('summaryTitleIcon', 'chart'))
    add(toolbar_layout, label('summaryHeading', 'Bảng điểm tổng hợp học kỳ', 12, True))
    add(toolbar_layout, label('summarySearchCaption', 'Tìm sinh viên:'))
    search = add(toolbar_layout, widget('QLineEdit', 'summarySearchEdit'))
    prop(search, 'placeholderText', 'Nhập mã SV hoặc họ tên...')
    prop(search, 'clearButtonEnabled', 'true', 'bool')
    size(search, 'minimumSize', 145, 28)
    size(search, 'maximumSize', 270, 16777215)
    add(toolbar_layout, button('summarySearchButton', ' Tìm', 'search', 30, 18))
    toolbar_layout.set('stretch', '0,1,0,1,0')
    body = add(card_layout, widget('QWidget', 'summaryTableBody'))
    body_layout = layout(body, 'QVBoxLayout', 'summaryTableBodyLayout', 6, 0)
    # Sample values reproduce the supplied reference image, not a grading rule.
    rows = [
        ['1', 'SV001', 'Nguyễn Văn An', '8.5', '7.5', '9.0', '8.39', 'Giỏi'],
        ['2', 'SV002', 'Trần Thị Bình', '7.0', '8.0', '7.5', '7.50', 'Khá'],
        ['3', 'SV003', 'Lê Minh Châu', '9.0', '9.5', '8.5', '9.66', 'Xuất sắc'],
        ['4', 'SV004', 'Phạm Quốc Dũng', '6.0', '7.0', '6.5', '6.56', 'Trung bình'],
        ['5', 'SV005', 'Hoàng Thị Giang', '8.0', '8.0', '8.5', '8.11', 'Giỏi'],
    ]
    summary = add(body_layout, table('summaryTable', [
        'STT', 'Mã SV', 'Họ và tên', 'Python\n(2 tín chỉ)', 'Cơ sở dữ liệu\n(3 tín chỉ)',
        'Toán\n(2 tín chỉ)', 'Điểm TB\n(học kỳ)', 'Xếp loại',
    ], rows))
    size(summary, 'minimumSize', 0, 174)

    bottom = add(content_layout, widget('QWidget', 'summaryBottom'))
    grid = layout(bottom, 'QGridLayout', 'summaryBottomLayout', 0, 12)
    grid.set('columnstretch', '30,46,24')

    def bottom_card(name, title, asset, column, width):
        card = add(grid, widget('QFrame', name), row='0', column=str(column))
        size(card, 'minimumSize', width, 168)
        card_layout = layout(card, 'QVBoxLayout', name + 'Layout', 0, 0)
        header = add(card_layout, widget('QFrame', name + 'Header'))
        header_layout = layout(header, 'QHBoxLayout', name + 'HeaderLayout', 6, 8)
        add(header_layout, image(name + 'Icon', asset))
        add(header_layout, label(name + 'Title', title, 11, True))
        body = add(card_layout, widget('QWidget', name + 'Body'))
        return layout(body, 'QVBoxLayout', name + 'BodyLayout', 6, 8)

    subjects_layout = bottom_card('subjectsCard', 'Thông tin môn học (học kỳ 1)', 'book', 0, 268)
    subjects = add(subjects_layout, table('subjectsTable', ['STT', 'Môn học', 'Số tín chỉ'], [
        ['1', 'Python', '3'], ['2', 'Cơ sở dữ liệu', '3'], ['3', 'Toán', '2'], ['', 'Tổng số tín chỉ', '8'],
    ]))
    size(subjects, 'minimumSize', 0, 132)
    size(subjects, 'maximumSize', 16777215, 132)
    prop(subjects, 'selectionMode', 'QAbstractItemView::NoSelection', 'enum')

    stats_layout = bottom_card('statisticsCard', 'Thống kê kết quả', 'pie', 1, 390)
    stats_body = add(stats_layout, widget('QWidget', 'statisticsBody'))
    stats_row = layout(stats_body, 'QHBoxLayout', 'statisticsBodyLayout', 0, 8)
    chip = add(stats_row, widget('QFrame', 'totalStudentsCard'))
    size(chip, 'minimumSize', 92, 104)
    size(chip, 'maximumSize', 108, 120)
    chip_layout = layout(chip, 'QVBoxLayout', 'totalStudentsLayout', 6, 2)
    spacer(chip_layout, 'totalStudentsTopSpacer')
    add(chip_layout, image('totalStudentsIcon', 'person_green', 28, 28), alignment='Qt::AlignHCenter')
    caption = add(chip_layout, label('totalStudentsCaption', 'Tổng số sinh viên', 8))
    prop(caption, 'alignment', 'Qt::AlignCenter', 'set')
    count = add(chip_layout, label('totalStudentsLabel', '5', 20, True))
    prop(count, 'alignment', 'Qt::AlignCenter', 'set')
    spacer(chip_layout, 'totalStudentsBottomSpacer')
    legend = add(stats_row, widget('QWidget', 'resultsLegend'))
    legend_layout = layout(legend, 'QGridLayout', 'resultsLegendLayout', 0, 6)
    for row, (name, text, color) in enumerate([
        ('excellent', 'Xuất sắc:  1 (20.0%)', '#42bf35'),
        ('good', 'Giỏi:        2 (40.0%)', '#b3f658'),
        ('fair', 'Khá:         1 (20.0%)', '#ffe35e'),
        ('average', 'Trung bình: 1 (20.0%)', '#ff9c9f'),
        ('weak', 'Yếu:         0 (0.0%)', '#bbc3cc'),
    ]):
        swatch = add(legend_layout, label(name + 'Swatch'), row=str(row), column='0')
        size(swatch, 'minimumSize', 13, 13)
        size(swatch, 'maximumSize', 13, 13)
        prop(swatch, 'styleSheet', f'background: {color}; border-radius: 3px;')
        add(legend_layout, label(name + 'LegendLabel', text, 8), row=str(row), column='1')
    add(stats_row, image('resultsChart', 'results_donut', 120, 120))
    stats_row.set('stretch', '0,1,0')
    actions = bottom_card('summaryActionsCard', 'Chức năng', 'gear', 2, 188)
    spacer(actions, 'summaryActionsTopSpacer')
    add(actions, button('summaryRefreshButton', ' Cập nhật dữ liệu', 'refresh'))
    add(actions, button('summaryExportButton', ' Xuất Excel', 'excel'))
    spacer(actions, 'summaryActionsBottomSpacer')

    style = ui.find('widget/property[@name="styleSheet"]/string')
    marker = '/* Semester overview */'
    base = style.text.split(marker)[0].rstrip()
    # Keep first-tab item styling while allowing summary cell background brushes.
    base = base.replace('QTableWidget::item {', 'QTableWidget#studentsTable::item {')
    style.text = base + '\n' + SUMMARY_STYLE
    prop(ui.find('.//widget[@name="mainTabs"]'), 'currentIndex', 1, 'number')
    stops = ui.find('tabstops')
    if stops is None:
        stops = ET.SubElement(ui, 'tabstops')
    for old in list(stops):
        if old.text in {'summarySearchEdit', 'summarySearchButton', 'summaryTable', 'subjectsTable', 'summaryRefreshButton', 'summaryExportButton'}:
            stops.remove(old)
    for name in ['summarySearchEdit', 'summarySearchButton', 'summaryTable', 'subjectsTable', 'summaryRefreshButton', 'summaryExportButton']:
        ET.SubElement(stops, 'tabstop').text = name
    ET.indent(ui, space=' ')
    tree.write(path, encoding='UTF-8', xml_declaration=True)


SUMMARY_STYLE = '''/* Semester overview */
QWidget#summaryContent, QWidget#summaryBottom, QScrollArea#summaryScroll { background: #f8fafc; }
QFrame#summaryGradesCard, QFrame#subjectsCard, QFrame#statisticsCard, QFrame#summaryActionsCard {
 background: #ffffff; border: 1px solid #cbdced; border-radius: 7px;
}
QFrame#summaryToolbar, QFrame#subjectsCardHeader, QFrame#statisticsCardHeader, QFrame#summaryActionsCardHeader {
 background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #d7eaff,stop:1 #c9e0fc);
 border: none; border-top-left-radius: 7px; border-top-right-radius: 7px;
}
QLabel#summaryHeading, QLabel#subjectsCardTitle, QLabel#statisticsCardTitle, QLabel#summaryActionsCardTitle { color: #004cce; }
QTableWidget#summaryTable, QTableWidget#subjectsTable { border: 1px solid #c0d0e3; gridline-color: #c7d1df; border-radius: 5px; alternate-background-color: #fafcff; }
QTableWidget#summaryTable QHeaderView::section, QTableWidget#subjectsTable QHeaderView::section {
 background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #d7eaff,stop:1 #c7e0fa);
 border-right: 1px solid #a9c8ed; border-bottom: 1px solid #b7cce5; padding: 5px 3px;
}
QFrame#totalStudentsCard { background: #e0fbd9; border: none; border-radius: 7px; }
QPushButton#summarySearchButton { background: #0079e8; border-color: #0069ce; color: white; padding: 4px 12px; }
QPushButton#summarySearchButton:hover { background: #0069cd; }
QPushButton#summaryRefreshButton { background: #eff6ff; border-color: #71aaff; color: #064fdf; padding: 6px 9px; }
QPushButton#summaryRefreshButton:hover { background: #dcecff; }
QPushButton#summaryExportButton { background: #effded; border-color: #47ae50; color: #078421; padding: 6px 9px; }
QPushButton#summaryExportButton:hover { background: #dbf6d6; }
'''


if __name__ == '__main__':
    build()
    print('Updated only the semester summary tab in main.ui.')
