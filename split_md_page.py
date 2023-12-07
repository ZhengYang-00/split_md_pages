import numpy as np
import PyPDF2
from tqdm import tqdm 
import sys

def remove_symbol(text):
    removed_text = ""
    symbol_list = ['•']
    # symbol_list = ['#','*','_','-','~','<','>','[',']','!','.',',','。','|','`','?','$','•',':']
    for s in text:
        if s in symbol_list:
            continue
        else:
            removed_text+=s
    return removed_text

def get_pdfpage_text(pdf_path, page_num):
    #page_num starts at 0
    with open(pdf_path,'rb') as fin:
        pdf_reader = PyPDF2.PdfReader(fin)
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



def dtw_string(pdf_text, md_text):
    if len(md_text) > 2*len(pdf_text):
        md_text = md_text[:2*len(pdf_text)]
    len_1 = len(pdf_text)
    len_2 = len(md_text)

    dtw_matrix = np.zeros((len_1 + 1, len_2 + 1))
    for i in range(1, len_1 + 1):
        for j in range(1, len_2 + 1):
            dist = abs(specified_ord(pdf_text[i-1])-specified_ord(md_text[j-1]))
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
    min_dist = np.inf
    min_k = 0
    last_valid_pdf_idx = -1
    while pdf_text[last_valid_pdf_idx] == ' ':
        last_valid_pdf_idx -= 1
    for k in range(len_1//2,len_2 + 1):
        if dtw_matrix[last_valid_pdf_idx][k] <= min_dist:
            min_dist = dtw_matrix[last_valid_pdf_idx][k]
            min_k = k
    path = get_path(len_1, min_k)
    path.reverse()
    return dtw_matrix, path


def split_whole_md(pdf_path, md_path):
    
    with open(md_path, 'r', encoding='utf-8') as fin:
        md_text = fin.read()
    with open(pdf_path,'rb') as fin:
        pdf_reader = PyPDF2.PdfReader(fin)
        mdtext_by_page = []
        for idx, page in tqdm(enumerate(pdf_reader.pages)):
            page_text = page.extract_text()
            page_text = remove_symbol(page_text)
            mat, path = dtw_string(page_text, md_text)
            start_md_idx, end_md_idx = path[0][1] -1, path[-1][1]
            with open(str(idx) + '.txt','w') as fout:
                original_stdout = sys.stdout
                sys.stdout = fout
                for r in path:
                    print(page_text[r[0]-1], md_text[r[1]-1])
                for k in range(len(page_text)//2,len(mat[-1])):
                    print(mat[-1][k], md_text[k-1])
                sys.stdout = original_stdout
            mdtext_by_page.append(md_text[start_md_idx:end_md_idx])
            md_text = md_text[end_md_idx:]
    return mdtext_by_page

