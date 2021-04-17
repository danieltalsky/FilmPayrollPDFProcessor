import subprocess


class PDFBox:
    """ Abstraction for command line calls to PDFBox """

    PDFBOX_JAR = "/root/pdfbox-app-2.0.23.jar"

    @classmethod
    def split_pages(cls, filepath: str):
        """
        Call PDFBox PDFSplit command line method on a a pdf with default options for a given filepath

        :param filepath:
        :return:
        """
        # print(f"   - Splitting PDF into pages:")
        result = subprocess.run([
            'java',
            '-jar',
            cls.PDFBOX_JAR,
            'PDFSplit',
            filepath
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # print(result.stdout)
        # error_messages = result.stderr
        # print(error_messages)

    @classmethod
    def merge_pages(cls, filepath_1: str, filepath_2: str, target_filepath: str):
        """
        Call PDFBox PDFMerger command line method to merge two PDFs

        :param filepath_1:
        :param filepath_2:
        :param target_filepath:
        :return:
        """
        # print(f"   - Splitting PDF into pages:")
        result = subprocess.run([
            'java',
            '-jar',
            cls.PDFBOX_JAR,
            'PDFMerger',
            filepath_1,
            filepath_2,
            target_filepath
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # print(result.stdout)
        # error_messages = result.stderr
        # print(error_messages)

    @classmethod
    def get_pdf_text(cls, filepath: str) -> str:
        """
        Call PDFBox ExtractText method on a pdf and return the text string extracted from the file

        :param filepath:
        :return:
        """
        result = subprocess.run([
            'java',
            '-jar',
            cls.PDFBOX_JAR,
            'ExtractText',
            filepath,
            '-console',
            'true'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output_string = result.stdout.decode('utf-8')
        error_string = result.stderr
        return output_string