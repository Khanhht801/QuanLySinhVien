"""Restore the compact input layout while preserving field text and table data."""
from pathlib import Path
from xml.etree import ElementTree as E

ROOT = Path(__file__).resolve().parents[1]


def repair():
    path = ROOT / 'main.ui'
    tree = E.parse(path)
    root = tree.getroot()

    def widget(name):
        return root.find(f'.//widget[@name="{name}"]')

    def find_layout(name):
        return root.find(f'.//layout[@name="{name}"]')

    def prop(element, name, value, kind='number'):
        for old in list(element.findall(f'property[@name="{name}"]')):
            element.remove(old)
        node = E.SubElement(E.SubElement(element, 'property', name=name), kind)
        if isinstance(value, dict):
            for key, val in value.items():
                E.SubElement(node, key).text = str(val)
        else:
            node.text = str(value)

    def size(element, name, width, height):
        prop(element, name, {'width': width, 'height': height}, 'size')

    def margins(layout, value, spacing=6):
        for side in ['left', 'top', 'right', 'bottom']:
            prop(layout, side + 'Margin', value)
        prop(layout, 'spacing', spacing)

    def make_widget(kind, name):
        return E.Element('widget', {'class': kind, 'name': name})

    def add(layout, child):
        E.SubElement(layout, 'item').append(child)

    # Apply the layout migration once; repeated calls retain the compact fonts.
    if widget('sidebarScroll') is None:
        for point in root.findall('.//font/pointsize'):
            value = int(point.text)
            point.text = str({25: 20, 19: 16, 17: 14, 15: 10, 13: 11, 12: 10, 11: 9}.get(value, value))
        prop(widget('MainWindow'), 'geometry', {'x': 0, 'y': 0, 'width': 1160, 'height': 640}, 'rect')
        size(widget('MainWindow'), 'minimumSize', 860, 480)
        for name, width, height in [('header', 0, 68), ('logoLabel', 66, 48)]:
            size(widget(name), 'minimumSize', width, height)
            size(widget(name), 'maximumSize', width or 16777215, height)
        size(widget('mainTabs'), 'iconSize', 20, 20)
        for name in ['studentHeading', 'subjectHeading']:
            size(widget(name), 'minimumSize', 0, 26)
        for item in root.findall('.//widget'):
            cls = item.get('class')
            if cls in ['QLineEdit', 'QComboBox']:
                size(item, 'minimumSize', 0, 28)
            elif cls in ['QSpinBox', 'QDoubleSpinBox']:
                size(item, 'minimumSize', 88, 26)
                size(item, 'maximumSize', 104, 26)
            elif cls == 'QPushButton':
                size(item, 'minimumSize', 80, 32)
                size(item, 'iconSize', 18, 18)
        size(widget('totalScoreLabel'), 'minimumSize', 104, 32)
        size(widget('searchEdit'), 'minimumSize', 80, 28)
        size(widget('filterSubjectCombo'), 'minimumSize', 140, 28)
        for name in ['entryLayout', 'headerLayout', 'summaryLayout']:
            if find_layout(name) is not None:
                margins(find_layout(name), 12, 12)
        for name in ['studentForm', 'subjectForm']:
            margins(find_layout(name), 8, 6)
        for name in ['sidebarLayout', 'tableAreaLayout', 'studentActionLayout', 'tableActionLayout']:
            margins(find_layout(name), 0, 8)
        margins(find_layout('searchLayout'), 8, 8)

        for card_name, form_name, body_name in [
            ('studentCardLayout', 'studentForm', 'studentFields'),
            ('subjectCardLayout', 'subjectForm', 'subjectFields'),
        ]:
            if widget(body_name) is None:
                form = find_layout(form_name)
                card = find_layout(card_name)
                item = next(item for item in card.findall('item') if form in list(item))
                item.remove(form)
                body = make_widget('QWidget', body_name)
                body.append(form)
                item.append(body)

        entry = find_layout('entryLayout')
        left_item = entry.findall('item')[0]
        sidebar_layout = find_layout('sidebarLayout')
        left_item.remove(sidebar_layout)
        column = make_widget('QWidget', 'sidebarColumn')
        size(column, 'minimumSize', 310, 0)
        size(column, 'maximumSize', 350, 16777215)
        column_layout = E.SubElement(column, 'layout', {'class': 'QVBoxLayout', 'name': 'sidebarColumnLayout'})
        margins(column_layout, 0, 8)
        scroll = make_widget('QScrollArea', 'sidebarScroll')
        prop(scroll, 'widgetResizable', 'true', 'bool')
        prop(scroll, 'frameShape', 'QFrame::NoFrame', 'enum')
        prop(scroll, 'horizontalScrollBarPolicy', 'Qt::ScrollBarAlwaysOff', 'enum')
        sidebar = make_widget('QWidget', 'sidebar')
        sidebar.append(sidebar_layout)
        scroll.append(sidebar)
        add(column_layout, scroll)
        for name, kind in [('sidebarDivider', 'widget'), ('studentActionLayout', 'layout')]:
            node = sidebar_layout.find(f'.//{kind}[@name="{name}"]')
            item = next(item for item in sidebar_layout.findall('item') if node in list(item))
            sidebar_layout.remove(item)
            column_layout.append(item)
        left_item.append(column)
        entry.set('stretch', '0,1')
        if widget('tableArea') is None:
            right_item = entry.findall('item')[1]
            right_layout = find_layout('tableAreaLayout')
            right_item.remove(right_layout)
            table_area = make_widget('QWidget', 'tableArea')
            table_area.append(right_layout)
            right_item.append(table_area)

        style = widget('MainWindow').find('property[@name="styleSheet"]/string')
        for before, after in [
            ('padding: 15px 22px', 'padding: 9px 14px'), ('margin-top: 16px', 'margin-top: 8px'),
            ('min-height: 22px', 'min-height: 18px'), ('padding: 5px 18px', 'padding: 4px 12px'),
            ('padding: 4px 10px', 'padding: 3px 8px'), ('padding: 10px 4px', 'padding: 7px 4px'),
            ('padding: 7px 17px', 'padding: 5px 10px'),
        ]:
            style.text = style.text.replace(before, after)
        style.text += '\nQScrollArea#sidebarScroll, QWidget#sidebar, QWidget#sidebarColumn { background: transparent; }\n'

    form = find_layout('subjectForm')
    coefficient_rows = {
        int(item.get('row')) for item in form.findall('item')
        if item.find('widget[@name="coefficientSpin"]') is not None
    }
    for item in list(form.findall('item')):
        row = int(item.get('row', '0'))
        if row in coefficient_rows:
            form.remove(item)
        else:
            item.set('row', str(row - sum(old < row for old in coefficient_rows)))
    for stops in root.findall('tabstops'):
        for stop in list(stops):
            if stop.text == 'coefficientSpin':
                stops.remove(stop)
    subtitle = widget('subtitleLabel').find('property[@name="text"]/string').text
    title = 'Quản lý điểm sinh viên - ' + ' - '.join(part.strip() for part in subtitle.split('|'))
    prop(widget('MainWindow'), 'windowTitle', title, 'string')
    E.indent(root, space=' ')
    tree.write(path, encoding='UTF-8', xml_declaration=True)


if __name__ == '__main__':
    repair()
    print('Restored compact input layout and removed the coefficient row.')
