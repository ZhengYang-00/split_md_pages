from split_md_page import split_whole_md
import PyPDF2


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



if __name__ == '__main__':
    pdf_filepath = '/home/zheng_yang/workspace/data-synthesis/tests/test_samples/md_label_generate/pdf/cn_test.pdf'
    md_filepath = '/home/zheng_yang/workspace/data-synthesis/tests/test_samples/md_label_generate/md/cn_test.md'
    mdtext_by_page = split_whole_md(pdf_path=pdf_filepath, md_path=md_filepath)
    for text in mdtext_by_page:
        print(text[-40:])


