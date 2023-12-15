import numpy as np
import pdfplumber
import PyPDF2
import fitz
from tqdm import tqdm 
import sys
import unicodedata
from copy import deepcopy
import Levenshtein

from modify_text import modify_text


def minNidx(dist_list:list, start_idx, end_idx):
    if start_idx < 0:
        start_idx = 0
    if end_idx > len(dist_list):
        end_idx = len(dist_list)
    min_value = dist_list[start_idx] + start_idx
    min_idx = start_idx
    for i in range(start_idx, end_idx):
        if dist_list[i] + i < min_value:
            min_value = dist_list[i] + i
            min_idx = i
    return min_value, min_idx

def match_score(char_1, char_2):
    return 1 - 8*(char_1==char_2)


def dtw_string(pdf_text, md_text, search_window = None):
    if len(md_text) > 2*len(pdf_text):
        md_text = md_text[:2*len(pdf_text)]
    len_1 = len(pdf_text)
    len_2 = len(md_text)
    if len_1 > len_2:
        raise ValueError('pdf text longer than latex text')

    dtw_matrix = np.zeros((len_1 + 1, len_2 + 1))
    if not search_window:
        for i in range(1, len_1 + 1):
            for j in range(1, len_2 + 1):
                dist = match_score(pdf_text[i-1],md_text[j-1])
                if dtw_matrix[i-1][j-1] != min(dtw_matrix[i-1][j], dtw_matrix[i][j-1],dtw_matrix[i-1][j-1]):
                    dtw_matrix[i][j] += min(dtw_matrix[i-1][j], dtw_matrix[i][j-1],dtw_matrix[i-1][j-1]) + dist + 7
                # dist = not(pdf_text[i-1] == md_text[j - 1]
                else:
                    dtw_matrix[i][j] = dist + min(dtw_matrix[i-1][j], dtw_matrix[i][j-1],dtw_matrix[i-1][j-1])
                # dist = not(pdf_text[i-1] == md_text[j - 1])
    else:
        for i in range(1, len_1 + 1):
            for j in range(i - search_window, i + search_window):
                if j <= 1 or j > len_2:
                    continue
                dist = match_score(pdf_text[i-1],md_text[j-1])
                if dtw_matrix[i-1][j-1] != min(dtw_matrix[i-1][j], dtw_matrix[i][j-1],dtw_matrix[i-1][j-1]):
                    dtw_matrix[i][j] += min(dtw_matrix[i-1][j], dtw_matrix[i][j-1],dtw_matrix[i-1][j-1]) + dist + 7
                # dist = not(pdf_text[i-1] == md_text[j - 1]
                else:
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
                elif dtw_matrix[i-1, j] == min(dtw_matrix[i-1, j-1], dtw_matrix[i-1, j], dtw_matrix[i, j-1]):
                    i -= 1
                else:
                    j -= 1
            path.append((i, j))
        return path
    last_valid_pdf_idx = -1
    while pdf_text[last_valid_pdf_idx] == ' ':
        last_valid_pdf_idx -= 1
    min_dist, min_idx = minNidx(dtw_matrix[last_valid_pdf_idx], 
                                len_1 + 1 + last_valid_pdf_idx - search_window,
                                len_1 + 1 + last_valid_pdf_idx + search_window
                                )
    path = get_path(len_1 + 1 + last_valid_pdf_idx, min_idx)
    path.reverse()
    return dtw_matrix, path


def check_module(raw_pdf_text, raw_md_text, compare_len, tolerance):
    try:
        pdf_end = raw_pdf_text[-compare_len:]
        md_end = raw_md_text[-compare_len:]
    except:
        raise ValueError('too long compare len')
    edit_dist = Levenshtein.distance(pdf_end, md_end)
    print(pdf_end, md_end, edit_dist)
    if edit_dist < tolerance:
        return True
    else:
        return False



def get_md_end_idx(mdt, search_window, in_code_block):
    raw_page_text, raw_md_text, numbyidx = mdt.result_text(in_code_block)
            
    mat, path = dtw_string(raw_page_text, raw_md_text, search_window=search_window)
    start_md_idx, end_md_idx = path[0][1] -1, path[-1][1] + numbyidx[path[-1][1]-1]
    return raw_page_text, raw_md_text, mat, path, start_md_idx, end_md_idx


def split_whole_md(pdf_path, md_path):
    
    init_windonw = 200
    reduce_scale = 0.7
    max_table_ctt = 10
    with open(md_path, 'r', encoding='utf-8') as fin:
        md_text = fin.read()
    #TODO:有表格的用pypdf，其他用pdfplumber，最好分页读取
    fin = open(pdf_path, 'rb')
    pdf_table_reader = PyPDF2.PdfReader(fin)

    with pdfplumber.open(pdf_path) as pdf_reader:
        mdtext_by_page = []
        in_code_block = False
        for idx in tqdm(range(len(pdf_reader.pages) - 1)):
            page = pdf_reader.pages[idx]
            page_text = page.extract_text()
            mdt = modify_text(page_text, md_text, search_window = init_windonw, scale=reduce_scale)
            copy_code_block = deepcopy(in_code_block)
            raw_page_text, raw_md_text, mat, path, start_md_idx, end_md_idx = get_md_end_idx(
                mdt, 
                init_windonw, 
                copy_code_block)
            # print(raw_md_text)
            table_content = mdt.extract_html_table_before_idx(end_md_idx) + mdt.extract_table_before_idx(end_md_idx, copy_code_block)
            if table_content and max([len(ctt) for ctt in table_content]) > max_table_ctt:
                # print('pdf table reader')
                page = pdf_table_reader.pages[idx]
                page_text = page.extract_text()
                mdt = modify_text(page_text, md_text, search_window = init_windonw, scale=reduce_scale)
                raw_page_text, raw_md_text, mat, path, start_md_idx, end_md_idx = get_md_end_idx(
                mdt, 
                init_windonw, 
                copy_code_block)
                in_code_block = mdt.end_of_md_in_code_block(end_md_idx, in_code_block)
            else:
                in_code_block = mdt.end_of_md_in_code_block(end_md_idx, in_code_block)

            with open(str(idx) + '.txt','w') as fout:
                original_stdout = sys.stdout
                sys.stdout = fout
                for r in path:
                    print(raw_page_text[r[0]-1], raw_md_text[r[1]-1])
                for k in range(len(page_text)//2,len(mat[-1])):
                    print(mat[-1][k], raw_md_text[k-1])
                print(page.extract_text())
                print(raw_md_text[:path[-1][1]])
                sys.stdout = original_stdout
            end_md_idx = mdt.complete_md_end(end_md_idx, in_code_block)
            mdtext_by_page.append(md_text[start_md_idx:end_md_idx])
            # print(len(page.extract_text()),len(md_text[start_md_idx:end_md_idx]))
            md_text = md_text[end_md_idx:]
            raw_md_text= raw_md_text[:path[-1][1]]
            print(check_module(raw_page_text, raw_md_text, 20, 5))
            print(mdtext_by_page[-1][-40:])
    fin.close()
    mdtext_by_page.append(md_text)
    return mdtext_by_page

