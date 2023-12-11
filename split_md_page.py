import numpy as np
import pdfplumber
from tqdm import tqdm 
import sys
import unicodedata

def remove_symbol(text):
    removed_text = ""
    symbol_list = ['•','◦','▪']
    # symbol_list = ['#','*','_','-','~','<','>','[',']','!','.',',','。','|','`','?','$','•',':']
    for s in text:
        if s in symbol_list:
            continue
        else:
            removed_text+=s
    return removed_text

def get_pdfpage_text(pdf_path, page_num):
    #page_num starts at 0
    with pdfplumber.open(pdf_path) as pdf_reader:
        if page_num - 1 > len(pdf_reader.pages):
            raise ValueError('page_num out of range')
        else:
            pdfpage_text = pdf_reader.pages[page_num].extract_text()
            start_idx = 0
            for i in range(page_num):
                start_idx += len(pdf_reader.pages[i].extract_text())

    return pdfpage_text, start_idx


def specified_ord(char):
    if '\u4e00' <= char <= '\u9fff':
        return ord(char)
    else:
        return ord(char) *1000
    
def normalize_math(str):
    return unicodedata.normalize('NFKC', str)


def remove_md_struct(pdf_text, md_text):
    # TODO md文件中，html格式的内容怎么删除
    #md中不会被渲染的字符，即解析的pdf中不会出现的字符
    # struct_chars =['|','-']
    struct_chars = ['#', '`', '*', '|', '$', ' ','-','~',' ','\n']
    deleted_chars_before_idx = []
    raw_md_text = ""
    deleted_num = 0
    i = 0
    while i < len(md_text)-2:
        char  = md_text[i]
        if char in struct_chars:
            deleted_num += 1
            i += 1
        elif char == '<':
            struct_deleted_num = deleted_num
            s_i = i
            while s_i < len(md_text) - 1 and md_text[s_i] != '>':
                struct_deleted_num += 1
                s_i += 1
                if s_i - i > 50:
                    deleted_chars_before_idx.append(deleted_num)
                    raw_md_text += char
                    i += 1
                    break
            if md_text[s_i] == '>':
                i = s_i + 1
                deleted_num = struct_deleted_num + 1
        else:
            deleted_chars_before_idx.append(deleted_num)
            raw_md_text += char
            i += 1
    raw_md_text += md_text[-2:]
    
    raw_pdf_text = ""
    for char in pdf_text:
        if char not in struct_chars:
            raw_pdf_text += char
    raw_pdf_text = raw_pdf_text.replace('\n','')

    return raw_pdf_text, raw_md_text, deleted_chars_before_idx

def minNidx(dist_list:list, start_idx, end_idx):
    min_value = dist_list[start_idx]
    min_idx = start_idx
    for i in range(start_idx, end_idx):
        if dist_list[i] < min_value:
            min_value = dist_list[i]
            min_idx = i
    return min_value, min_idx


def dtw_string(pdf_text, md_text, window = 0):
    if len(md_text) > 2*len(pdf_text):
        md_text = md_text[:2*len(pdf_text)]
    len_1 = len(pdf_text)
    len_2 = len(md_text)
    if len_1 > len_2:
        raise ValueError('pdf text shorter than latex text')

    dtw_matrix = np.zeros((len_1 + 1, len_2 + 1))
    for i in range(1, len_1 + 1):
        for j in range(1, len_2 + 1):
            dist = sum([2 - 3*(pdf_text[i_w-1] == md_text[j_w-1]) if i_w -1 >=0 and i_w<=len_1 and j_w -1 >=0 and j_w<=len_2 
                        else 0
                        for (i_w, j_w) in zip(range(i-window,i+window+1),
                                              range(j-window,j+window+1))])
            # dist = not(pdf_text[i-1] == md_text[j - 1])
            dtw_matrix[i][j] = dist + min(dtw_matrix[i-1][j], dtw_matrix[i][j-1],dtw_matrix[i-1][j-1])
    def get_path(i,j):
        path = [(i,j)]
        while i > 1 or j > 1:
            if i == 1:
                j -= 1
            elif j == 1:
                i -= 1
            else:
                # 找到最小邻居
                if dtw_matrix[i-1, j-1] == min(dtw_matrix[i-1, j-1], dtw_matrix[i-1, j], dtw_matrix[i, j-1]):
                    i -= 1
                    j -= 1
                elif dtw_matrix[i, j-1] == min(dtw_matrix[i-1, j-1], dtw_matrix[i-1, j], dtw_matrix[i, j-1]):
                    j -= 1
                else:
                    i -= 1
            path.append((i, j))
        return path
    last_valid_pdf_idx = -1
    while pdf_text[last_valid_pdf_idx] == ' ':
        last_valid_pdf_idx -= 1
    min_dist, min_idx = minNidx(dtw_matrix[last_valid_pdf_idx], len_1//2, len_2+1)
    path = get_path(len_1 + 1 + last_valid_pdf_idx, min_idx)
    path.reverse()
    return dtw_matrix, path


def split_whole_md(pdf_path, md_path):
    
    with open(md_path, 'r', encoding='utf-8') as fin:
        md_text = fin.read()
    with pdfplumber.open(pdf_path) as pdf_reader:
        mdtext_by_page = []
        for idx, page in tqdm(enumerate(pdf_reader.pages[:-1])):
            page_text = page.extract_text()
            # 去掉页码
            # if page_text[-1] == str(idx + 1):
            #     page_text = page_text[:-1] 
            page_text = remove_symbol(page_text)
            page_text = normalize_math(page_text)
            # raw_md_text = md_text
            page_text, raw_md_text, numbyidx = remove_md_struct(page_text, md_text)
            mat, path = dtw_string(page_text, raw_md_text, window=0)
            start_md_idx, end_md_idx = path[0][1] -1, path[-1][1] + numbyidx[path[-1][1]-1]
            with open(str(idx) + '.txt','w') as fout:
                original_stdout = sys.stdout
                sys.stdout = fout
                for r in path:
                    print(page_text[r[0]-1], raw_md_text[r[1]-1])
                for k in range(len(page_text)//2,len(mat[-1])):
                    print(mat[-1][k], raw_md_text[k-1])
                print(page_text)
                sys.stdout = original_stdout
            mdtext_by_page.append(md_text[start_md_idx:end_md_idx])
            md_text = md_text[end_md_idx:]
    mdtext_by_page.append(md_text)
    return mdtext_by_page

