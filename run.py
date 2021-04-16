import hashlib
import os
from pathlib import Path
import re
from shutil import copyfile
import subprocess


INBOX_FOLDER_PATH = '/home/pdfs/inbox/'
OUTBOX_FOLDER_PATH = '/home/pdfs/outbox/'
# PROCESSING_FOLDER_PATH = '/home/pdfs/processing/'
PROCESSING_FOLDER_PATH = '/tmp/'

OUTBOX_CHECK_COPY_FOLDER = 'check_copies'
OUTBOX_TIME_CARD_FOLDER = 'time_cards'
OUTBOX_MERGE_FOLDER = 'final'


def main():
    """ Iterates through pdfs in the PDF Inbox """

    unmatched_time_cards = []
    unmatched_check_copies = []
    for filename in os.listdir(INBOX_FOLDER_PATH):

        # File Type Detection
        if filename.endswith(".pdf") and filename.startswith("WE_"):
            print(f"\nDetected TimeCards file for processing: {filename}")
            unmatched_time_cards = unmatched_time_cards + \
                PayrollProcess.process_multi_page_time_card(
                    os.path.join(INBOX_FOLDER_PATH, filename)
                )
        elif filename.endswith(".pdf"):
            print(f"\nDetected PDF file for processing, processing as Check Copies package: {filename}")
            unmatched_check_copies = unmatched_check_copies + \
                PayrollProcess.process_multi_page_check_copies_package(
                    os.path.join(INBOX_FOLDER_PATH, filename)
                )
        elif filename.endswith(".txt"):
            pass
        else:
            print(f"\nSKIPPING: File found but not identified: {filename}")

    print(f"\nFiles written, wrote {len(unmatched_time_cards)} time cards and {len(unmatched_check_copies)} check copies")
    PayrollProcess.match_time_cards_to_check_copies(
        unmatched_time_cards,
        unmatched_check_copies
    )


class PayrollProcess:

    @classmethod
    def _copy_to_temp_file(cls, original_filepath: str):
        """
        Creates a temporary

        :param original_filepath:
        :return hash_string, full_path: a tuple with the hashed filename and the full path to the newly created filename
        """
        hash_string = hashlib.md5(original_filepath.encode('utf-8')).hexdigest()
        temp_name = f"{hash_string}.pdf"
        full_path = os.path.join(PROCESSING_FOLDER_PATH, temp_name)

        # copy file to temp directory for processing
        copyfile(original_filepath, full_path)
        return hash_string, full_path

    @classmethod
    def _read_check_copy_list(cls, check_copy_list_path: str) -> list:
        """
        Parses a list of checks in a check copy package

        Example:
            Date:04/03/2021
            PAGE,LAST,FIRST,INVOICE,AMOUNT
            12,PINCKLEY,DENISE,EYM788,7094.97
            13,PINCKLEY,DENISE,EYM788,4682.00

        :param check_copy_list_path:
        :return:
        """
        check_copy_list = []
        month = ""
        day = ""
        year = ""
        with open(check_copy_list_path) as check_copy_list_file:
            check_copy_string = check_copy_list_file.read()
            # print(check_copy_string)
        for line in check_copy_string.splitlines():
            if "Date:" in line:
                line = line.replace("Date:", "")
                line = line.replace(" ", "")
                fields = line.split("/")
                month = fields[0]
                day = fields[1]
                year = fields[2]
            elif "PAGE,LAST,FIRST,INVOICE,AMOUNT" in line:
                pass
            else:
                fields = line.split(",")
                if len(fields) >= 4:
                    page = fields[0]
                    last = fields[1]
                    first = fields[2]
                    invoice = fields[3]
                    amount = fields[4]

                    check_copy = CheckCopyPDFPage(
                        month=month,
                        day=day,
                        year=year,
                        page_number=page,
                        payee_last_name=last,
                        payee_first_name=first,
                        invoice_number=invoice,
                        check_amount_string=amount
                    )
                    check_copy_list.append(check_copy)
        return check_copy_list

    @classmethod
    def _cleanup_temp_files(cls, hash_string):
        """ Cleanup the original and split files in the processing directory based on original temp name hash"""
        cleanup_list = []
        for filename in os.listdir(PROCESSING_FOLDER_PATH):
            if filename.startswith(hash_string):
                process_page_path = os.path.join(PROCESSING_FOLDER_PATH, filename)
                cleanup_list.append(process_page_path)
        for file_path in cleanup_list:
            os.remove(file_path)

    @classmethod
    def process_multi_page_check_copies_package(cls, filepath: str) -> list:
        """
        Splits a multi-page PDF into individual pages and then processes those pages

        :param filepath:
        :return:
        """

        # check for list file
        unmatched_check_copies = []
        expected_check_copy_list_path = filepath.replace(".pdf", ".txt")
        if Path(expected_check_copy_list_path).exists():
            unmatched_check_copies = cls._read_check_copy_list(expected_check_copy_list_path)
            print(f" - Check copy list found with {len(unmatched_check_copies)}")
        else:
            print(f" - WARNING: No check list found for {filepath}, need {expected_check_copy_list_path}")

        hash_string, temp_path = cls._copy_to_temp_file(filepath)

        print(" - Splitting file into pages...")
        PDFBox.split_pages(temp_path)
        print(" - Finished splitting")

        print(" - Looking for split pages...")
        for filename in os.listdir(PROCESSING_FOLDER_PATH):
            # PDFBox uses a filename-n.pdf naming convention by default
            page_prefix = f"{hash_string}-"
            if filename.startswith(page_prefix):
                page_number = filename.replace(page_prefix, "").replace(".pdf", "")
                print(f"   - Found page {page_number}")
                filepath = os.path.join(PROCESSING_FOLDER_PATH, filename)
                for i, check_copy in enumerate(unmatched_check_copies):
                    if check_copy.page_number == page_number:
                        output_filepath = os.path.join(
                            OUTBOX_FOLDER_PATH,
                            OUTBOX_CHECK_COPY_FOLDER,
                            check_copy.output_file_name
                        )
                        copyfile(filepath, output_filepath)
                        print(f"     - Found page record - Will be named: {output_filepath}")
                        unmatched_check_copies[i].pdf_page_found = True
                        break

        cls._cleanup_temp_files(hash_string)

        return unmatched_check_copies

    @classmethod
    def process_multi_page_time_card(cls, filepath: str) -> list:
        """
        Splits a multi-page PDF into individual pages and then processes those pages

        :param filepath:
        :return:
        """
        hash_string, temp_path = cls._copy_to_temp_file(filepath)

        # copy file to temp directory for processing
        copyfile(filepath, temp_path)

        print(" - Splitting file into pages...")
        PDFBox.split_pages(temp_path)
        print(" - Finished splitting")

        print(" - Looking for split pages...")
        unmatched_time_cards = []
        for filename in os.listdir(PROCESSING_FOLDER_PATH):
            # PDFBox uses a filename-n.pdf naming convention by default
            page_prefix = f"{hash_string}-"
            if filename.startswith(page_prefix):
                page_number = filename.replace(page_prefix, "").replace(".pdf", "")
                print(f"   - Found page {page_number}")
                filepath = os.path.join(PROCESSING_FOLDER_PATH, filename)
                text = PDFBox.get_pdf_text(filepath)
                # print("--- start debugging time card text ---")
                # print(text)
                # print("--- end debugging time card text ---")
                page = TimeCardPDFPage(text)
                if page.is_end_of_batch():
                    print(f"   - Detected END of BATCH page")
                else:
                    page.verify_extracted_information()

                    print(f"   - Detected TimeCard - Will be named: {page.output_file_name}")
                    output_filepath = os.path.join(
                        OUTBOX_FOLDER_PATH,
                        OUTBOX_TIME_CARD_FOLDER,
                        page.output_file_name
                    )
                    copyfile(filepath, output_filepath)
                    unmatched_time_cards.append(page)

        cls._cleanup_temp_files(hash_string)
        return unmatched_time_cards

    @classmethod
    def match_time_cards_to_check_copies(
        cls,
        unmatched_time_cards: list,
        unmatched_check_copies: list
    ):
        """
        Match time cards to check copies and merge into a single PDF

        Example:
        LLS2-PR-TC-PINCKLEY,DENISE-20210403-EYM788
        LLS2-PR-TC-02-PINCKLEY,DENISE-20210403-EYM788

        :param unmatched_time_cards:
        :param unmatched_check_copies:
        :return:
        """
        # enumerate over copies of the unmatched lists so I can pull out matches during iteration
        matched_time_cards = []
        matched_check_copies = []
        payee_name_counter = dict()
        print("\nMatching time cards to check copies:")
        for tc in unmatched_time_cards:
            for cc in unmatched_check_copies:
                # tc = TimeCardPDFPage
                # cc = CheckCopyPDFPage
                if (
                    tc.last_name == cc.payee_last_name and
                    tc.first_name == cc.payee_first_name and
                    tc.grand_total_amount_in_cents == cc.check_amount_in_cents and
                    tc.pay_period_month_string == cc.month and
                    tc.pay_period_day_string == cc.day and
                    tc.pay_period_year_string == cc.year
                ):
                    print(f"- {tc.output_file_name} <matched> {cc.output_file_name}")
                    matched_time_cards.append(tc)
                    matched_check_copies.append(cc)

                    # increment name counter so we can number multiple checks by the same person
                    name_key = f"{tc.last_name},{tc.first_name}"
                    if name_key in payee_name_counter.keys():
                        payee_name_counter[name_key] += 1
                    else:
                        payee_name_counter[name_key] = 1

                    # Create merged file
                    tc_hash, tc_temp_path = PayrollProcess._copy_to_temp_file(
                        os.path.join(
                            OUTBOX_FOLDER_PATH,
                            OUTBOX_TIME_CARD_FOLDER,
                            tc.output_file_name
                        )
                    )
                    cc_hash, cc_temp_path = PayrollProcess._copy_to_temp_file(
                        os.path.join(
                            OUTBOX_FOLDER_PATH,
                            OUTBOX_CHECK_COPY_FOLDER,
                            cc.output_file_name
                        )
                    )
                    merged_temp_path = cc_temp_path + "-merged"
                    PDFBox.merge_pages(
                        tc_temp_path,
                        cc_temp_path,
                        merged_temp_path
                    )
                    output_file_name = cc.merged_output_name(nth_check=payee_name_counter[name_key])
                    print(f"   - Writing merged file to {output_file_name}")
                    final_output_path = os.path.join(
                        OUTBOX_FOLDER_PATH,
                        OUTBOX_MERGE_FOLDER,
                        output_file_name
                    )
                    copyfile(
                        merged_temp_path,
                        final_output_path
                    )
                    PayrollProcess._cleanup_temp_files(tc_hash)
                    PayrollProcess._cleanup_temp_files(cc_hash)

        # remove matches from unmatched lists
        for matched_tc in matched_time_cards:
            unmatched_time_cards.remove(matched_tc)
        for matched_cc in matched_check_copies:
            unmatched_check_copies.remove(matched_cc)

        print("\nFinished.")
        print("\nThe following time cards were not matched to a check copy:")
        for time_card in sorted(unmatched_time_cards, key=lambda x: x.output_file_name):
            print(f" - {time_card.output_file_name}")

        print("\nThe following check copies were not matched to a time card:")
        for check_copy in sorted(unmatched_check_copies, key=lambda x: x.output_file_name):
            print(f" - {check_copy.output_file_name}")


class PDFBox:
    """ Abstraction for command line calls to PDFBox """

    PDFBOX_JAR = "/root/pdfbox-app-2.0.23.jar"

    @classmethod
    def split_pages(cls, filepath: str):
        """
        Call PDFBox PDFSplit command line method ona a pdf with default options for a given filepath

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


class CheckCopyPDFPage:

    month: str
    day: str
    year: str
    page_number: str
    payee_last_name: str
    payee_first_name: str
    invoice_number: str
    check_amount_in_cents: int

    pdf_page_found: bool = False

    def __init__(
            self,
            month: str,
            day: str,
            year: str,
            page_number: str,
            payee_last_name: str,
            payee_first_name: str,
            invoice_number: str,
            check_amount_string: str
    ):
        self.month = month
        self.day = day
        self.year = year
        self.page_number = page_number
        self.payee_last_name = payee_last_name
        self.payee_first_name = payee_first_name
        self.invoice_number = invoice_number

        # remove commas
        check_amount_string = check_amount_string.replace(",", "")

        # sometimes the amount is truncated like 1,293.3
        amount_list = check_amount_string.split(".")
        if len(amount_list[1]) < 2:
            check_amount_string = check_amount_string + "0"

        check_amount_string = check_amount_string.replace(".", "")

        self.check_amount_in_cents = int(check_amount_string)

    @property
    def output_file_name(self):
        # Format: "CC-Last,First-031321-ECY879-74039.00.pdf"
        first_name = self.payee_first_name
        last_name = self.payee_last_name
        month = self.month
        day = self.day
        year = self.year
        invoice = self.invoice_number
        output_amount = "{:.2f}".format(self.check_amount_in_cents/100)
        return f"CC-{last_name},{first_name}-{month}{day}{year}-{invoice}-{output_amount}.pdf"

    def merged_output_name(self, nth_check: int = 1):
        """
        Generates a name for the file merged with

        Example:
        LLS2-PR-TC-PINCKLEY,DENISE-20210403-EYM788
        LLS2-PR-TC-02-PINCKLEY,DENISE-20210403-EYM788

        :param nth_check:
        :return:
        """

        counter = ""
        if nth_check > 1:
            counter = f"-0{str(nth_check)}"
        last = self.payee_last_name
        first = self.payee_first_name
        date = self.month + self.day + self.year
        invoice = self.invoice_number

        return f"LLS2-PR-TC{counter}-{last},{first},{date}-{invoice}.pdf"


class TimeCardPDFPage:
    """
    Models the important data in a split time card PDF page
    """

    END_OF_BATCH_INDICATOR = "END of BATCH"

    raw_page_text: str

    first_name: str = False
    last_name: str = False
    pay_period_day_string: str = False
    pay_period_month_string: str = False
    pay_period_year_string: str = False
    grand_total_amount_in_cents: int = False

    def __init__(self, raw_page_text):
        self.raw_page_text = raw_page_text
        self.extract_name()
        self.extract_pay_period_date()
        self.extract_grand_total_amount()

    def verify_extracted_information(self):
        missing_information = []
        if not self.first_name or not self.last_name:
            missing_information.append("Payee name")
        if not self.pay_period_month_string or not self.pay_period_day_string or not self.pay_period_year_string:
            missing_information.append("Pay period ending date")
        if not self.grand_total_amount_in_cents:
            # missing_information.append("Grand total amount")
            self.grand_total_amount_in_cents = 0
        if len(missing_information):
            missing = ", ".join(missing_information)
            error = f"ERROR: Couldn't get the following information from this file: {missing}"
            error += "Raw information from the PDF:"
            error += f"\n -------- \n {self.raw_page_text} \n ------- \n"
            raise Exception(error)

    def is_end_of_batch(self) -> bool:
        """
        Checks in a PDF time card page to see if the page is an "end of batch" placeholder page

        :return:
        """
        return self.END_OF_BATCH_INDICATOR in self.raw_page_text

    @property
    def output_file_name(self):
        # Format: "TC-Last,First-031321.pdf"
        first_name = self.first_name
        last_name = self.last_name
        day = self.pay_period_day_string
        month = self.pay_period_month_string
        year = self.pay_period_year_string
        output_amount = "{:.2f}".format(self.grand_total_amount_in_cents/100)
        return f"TC-{last_name},{first_name}-{month}{day}{year}-{output_amount}.pdf"

    def extract_name(self):
        # Example: "LIDDIARD, JOAQUIN SSN"
        # Example: "PINCKLEY, DENISE"
        for line in self.raw_page_text.splitlines():
            if "," in line:
                name_list = line.split(", ")
                self.last_name = name_list[0]
                self.first_name = name_list[1]
                # strip middle initial / SSN label
                if " " in self.first_name:
                    self.first_name = self.first_name.split(" ").pop(0)
                break

    def extract_pay_period_date(self):
        # Example: "03/13/2021Pay Period Ending :"
        for line in self.raw_page_text.splitlines():
            if "Pay Period Ending" in line:
                date_string = line.split("Pay").pop(0)
                date_list = date_string.split("/")
                self.pay_period_month_string = date_list[0]
                self.pay_period_day_string = date_list[1]
                self.pay_period_year_string = date_list[2]
                break

    def extract_grand_total_amount(self):
        """
        Extract the grand total to match with checks

        When we see the "Grand Total" line, start collecting amounts

        Example:
            Grand Total:
        165,687.3
        165,687.3
        Split Coding

        Example:
            Grand Total:
        50.0 5,740.00
        1,006.00
        6,746.00
        Split Coding

        :return:
        """
        capture_total_amounts: bool = False
        last_total_amount: str = False
        for line in self.raw_page_text.splitlines():
            # print(f"Line examined: {line}")
            if "Split Coding" in line:
                break
            elif capture_total_amounts:
                check_dollar_amount_pattern = r'^[0-9,]+\.[0-9]{1,2}$'
                if re.match(check_dollar_amount_pattern, line):
                    last_total_amount = line
            elif "Grand Total" in line:
                capture_total_amounts = True

        if last_total_amount:
            # remove commas
            last_total_amount = last_total_amount.replace(",", "")

            # sometimes the amount is truncated like 1,293.3
            amount_list = last_total_amount.split(".")
            if len(amount_list[1]) < 2:
                last_total_amount = last_total_amount + "0"

            last_total_amount = last_total_amount.replace(".", "")
            self.grand_total_amount_in_cents = int(last_total_amount)


if __name__ == '__main__':
    main()
