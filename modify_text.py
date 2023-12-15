import unicodedata
from bs4 import BeautifulSoup


class modify_text(object):
    def __init__(self, pdf_text, md_text, search_window, scale) -> None:
        self.pdf_text = pdf_text
        self.md_text = md_text
        self.window = search_window
        self.reduce_scale = scale
        self.deleted_chars_before_idx = list()
        self.raw_md_text = ""
        self.raw_pdf_text = ""
    
    def remove_symbol(self):
        symbol_list = ['•','◦','▪']
        for s in symbol_list:
            self.pdf_text = self.pdf_text.replace(s,'')
        
        return self.pdf_text
    
    def normalize_math(self):
        self.pdf_text = unicodedata.normalize('NFKC', self.pdf_text)
        return self.pdf_text
    
    def end_of_md_in_code_block(self, end_idx, in_code_block = False):
        for char in self.md_text[:end_idx]:
            if char == '`':
                in_code_block = not in_code_block
        
        return in_code_block

    
    def remove_md_struct(self, in_code_block = False):
        # md中不会被渲染的字符，即解析的pdf中不会出现的字符
        struct_chars = [' ','\n','\t']
        md_chars = ['|','-','#','*']
        # ['|','-','#','*']
        deleted_num = 0
        i = 0
        while i < len(self.md_text)-2:
            char  = self.md_text[i]
            if char in struct_chars:
                deleted_num += 1
                i += 1
                continue
            if char == '`':
                in_code_block = not in_code_block
                deleted_num += 1
                i += 1
                continue
            elif in_code_block:
                self.deleted_chars_before_idx.append(deleted_num)
                self.raw_md_text += char
                i += 1
                continue
            elif char in md_chars:
                deleted_num += 1
                i += 1
            elif char == '<':
                struct_deleted_num = deleted_num
                s_i = i
                while s_i < len(self.md_text) - 1 and self.md_text[s_i] != '>':
                    struct_deleted_num += 1
                    s_i += 1
                    if s_i - i > self.window * self.reduce_scale:
                        self.deleted_chars_before_idx.append(deleted_num)
                        self.raw_md_text += char
                        i += 1
                        break
                if self.md_text[s_i] == '>':
                    i = s_i + 1
                    deleted_num = struct_deleted_num + 1
            else:
                self.deleted_chars_before_idx.append(deleted_num)
                self.raw_md_text += char
                i += 1
        self.raw_md_text += self.md_text[-2:]
    
        for char in self.pdf_text:
            if char not in struct_chars + md_chars:
                self.raw_pdf_text += char
        return self.raw_pdf_text, self.raw_md_text, self.deleted_chars_before_idx
    

    def extract_table_before_idx(self, idx=None, in_code_block = False):
        if not idx:
            idx = len(self.pdf_text)*2 if len(self.md_text) > 2*len(self.pdf_text) else len(self.md_text)
        md2check = self.md_text[:idx]
        md_lines = md2check.split('\n')
        line_cnt = len(md_lines)
        md2check = "\n".join(md_lines[-line_cnt//4:])
        cell_content = list()
        i = 0
        len_md = len(md2check)
        while i < len_md:
            if md2check[i] == '`':
                in_code_block = not in_code_block
                i += 1
                continue
            if md2check[i] == '|':
                i += 1
                single_cell = ""
                while i < len_md and md2check[i] != '|' and md2check[i] != '\n':
                    if md2check[i] != '-':
                        single_cell += md2check[i]
                    i += 1

                if single_cell and (i >= len_md or md2check[i] !='\n'):
                    cell_content.append(single_cell)
            else:
                i += 1
        return cell_content
    
    def extract_html_table_before_idx(self, idx=None):
        if not idx:
            idx = len(self.pdf_text)*2 if len(self.md_text) > 2*len(self.pdf_text) else len(self.md_text)
        md2check = self.md_text[:idx]
        md_lines = md2check.split('\n')
        line_cnt = len(md_lines)
        md2check = "\n".join(md_lines[-line_cnt//4:])
        cell_content = list()
        soup = BeautifulSoup(md2check,'html.parser')
        tables = soup.find_all('tr')
        for row in tables:
            cols = row.find_all(['td','th'])
            cell_content.extend([col.text for col in cols])
        return cell_content
    

    def result_text(self, in_code_block = False):
        self.remove_symbol()
        self.normalize_math()
        return self.remove_md_struct(in_code_block)
    
    def complete_md_end(self, end_idx, in_code_block):
        # 补全代码块和html格式的末尾，补全表格
        new_end_idx = end_idx
        margin = 5
        igore_list = [' ','\n','\t']
        for idx in range(margin):
            try:
                char = self.md_text[end_idx + idx]
            except:
                break
            if char in igore_list:
                continue
            if char == '<':
                i = end_idx + idx + 1
                while i < len(self.md_text) and self.md_text[i] != '>':
                    i += 1
            
                new_end_idx = i + 1
                return new_end_idx
            elif char == '|':
                new_end_idx = end_idx + idx + 1
                return new_end_idx
            elif char == '`':
                if not in_code_block:
                    return new_end_idx
                i = end_idx + idx + 1
                while i < len(self.md_text) and self.md_text[i] == '`':
                    i += 1
                new_end_idx = i
                return new_end_idx
            else:
                break
        return new_end_idx
    






        


    

