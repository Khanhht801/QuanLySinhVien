"""Write genuine XLSX workbooks; student text is never interpreted as formulas."""
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def export_workbook(path, title, headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Bảng điểm K10TIN'
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    sheet.cell(1, 1, title).font = Font(name='Calibri', size=16, bold=True, color='0056B7')
    sheet.cell(2, 1, 'Xuất lúc: ' + datetime.now().strftime('%d/%m/%Y %H:%M'))
    for column, header in enumerate(headers, 1):
        cell = sheet.cell(3, column, header)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='0069B9')
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    edge = Side(style='thin', color='D5DCE5')
    category_fills = {'Giỏi': 'DFFBD5', 'Khá': 'FFF5CD', 'Trung bình': 'FFDCD8', 'Trung bình yếu': 'FFC9CE', 'Kém': 'FFABB0', 'Chưa đủ điểm': 'EEF1F5'}
    for row_number, values in enumerate(rows, 4):
        for column, value in enumerate(values, 1):
            cell = sheet.cell(row_number, column, value)
            if isinstance(value, str):
                cell.data_type = 's'
            elif isinstance(value, float):
                cell.number_format = '0.00'
            cell.border = Border(left=edge, right=edge, top=edge, bottom=edge)
            cell.alignment = Alignment(vertical='center', horizontal='left' if column == 3 else 'center')
            if row_number % 2 == 1:
                cell.fill = PatternFill('solid', fgColor='F5F9FE')
        category = values[-1] if values else ''
        if category in category_fills:
            category_columns = [len(values)]
            if 'Điểm TBC học kỳ' in headers:
                category_columns.append(headers.index('Điểm TBC học kỳ') + 1)
            elif len(values) > 1:
                category_columns.append(len(values) - 1)
            for column in category_columns:
                sheet.cell(row_number, column).fill = PatternFill('solid', fgColor=category_fills[category])
                sheet.cell(row_number, column).font = Font(bold=True)
    sheet.row_dimensions[3].height = 34
    for column, header in enumerate(headers, 1):
        longest = max([len(line) for line in str(header).split('\n')] + [len(str(row[column-1] or '')) for row in rows])
        sheet.column_dimensions[get_column_letter(column)].width = min(38, max(12, longest + 3))
    sheet.freeze_panes = 'D4'
    sheet.auto_filter.ref = f'A3:{get_column_letter(len(headers))}{max(3, len(rows)+3)}'
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = 'landscape'
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.print_title_rows = '1:3'
    workbook.save(path)
