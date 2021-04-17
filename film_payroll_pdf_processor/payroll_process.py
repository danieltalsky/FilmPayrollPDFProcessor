import hashlib
import os
from pathlib import Path
from shutil import copyfile

from film_payroll_pdf_processor.pdfbox_wrapper import PDFBox
from film_payroll_pdf_processor.pdf_pages import TimeCardPDFPage, CheckCopyPDFPage

INBOX_FOLDER_PATH = '/home/pdfs/inbox/'
OUTBOX_FOLDER_PATH = '/home/pdfs/outbox/'
# PROCESSING_FOLDER_PATH = '/home/pdfs/processing/'
PROCESSING_FOLDER_PATH = '/tmp/'

OUTBOX_CHECK_COPY_FOLDER = 'check_copies'
OUTBOX_TIME_CARD_FOLDER = 'time_cards'
OUTBOX_MERGE_FOLDER = 'final'


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
            PAGE,LAST,FIRST,INVOICE
            12,PINCKLEY,DENISE,EYM788
            13,PINCKLEY,DENISE,EYM788

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
            elif "PAGE,LAST,FIRST,INVOICE" in line:
                pass
            else:
                fields = line.split(",")
                if len(fields) >= 4:
                    page = fields[0]
                    last = fields[1]
                    first = fields[2]
                    invoice = fields[3]

                    check_copy = CheckCopyPDFPage(
                        month=month,
                        day=day,
                        year=year,
                        page_number=page,
                        payee_last_name=last,
                        payee_first_name=first,
                        invoice_number=invoice,
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

        print(" - Splitting file into pages...")
        hash_string, temp_path = cls._copy_to_temp_file(filepath)
        PDFBox.split_pages(temp_path)
        print(" - Finished splitting")

        # print(" - Looking for split pages...")
        duplicate_check_copy_set = set()
        for filename in os.listdir(PROCESSING_FOLDER_PATH):
            # PDFBox uses a filename-n.pdf naming convention by default
            page_prefix = f"{hash_string}-"
            if filename.startswith(page_prefix):
                page_number = filename.replace(page_prefix, "").replace(".pdf", "")
                print(f"   - Found page {page_number}")
                filepath = os.path.join(PROCESSING_FOLDER_PATH, filename)
                for i, check_copy in enumerate(unmatched_check_copies):
                    if check_copy.page_number == page_number:
                        # Check for a duplicate record that is the same name,date and invoice number and mark
                        duplicate_check_copy_item = (
                            check_copy.payee_first_name,
                            check_copy.payee_last_name,
                            check_copy.month,
                            check_copy.day,
                            check_copy.year,
                            check_copy.invoice_number
                        )
                        if duplicate_check_copy_item in duplicate_check_copy_set:
                            unmatched_check_copies[i].payee_first_name = check_copy.payee_first_name + "_DUPLICATE_TC"
                            unmatched_check_copies[i].payee_last_name = check_copy.payee_last_name + "_DUPLICATE_TC"
                            print(f'Detected duplicate!  Marking file: {check_copy.output_file_name}')
                        else:
                            duplicate_check_copy_set.add(duplicate_check_copy_item)

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
    def process_multi_page_time_card(cls, filepath: str, is_revision: bool = False) -> list:
        """
        Splits a multi-page PDF into individual pages and then processes those pages

        :param filepath:
        :return:
        """
        original_filepath = filepath
        hash_string, temp_path = cls._copy_to_temp_file(filepath)

        # copy file to temp directory for processing
        copyfile(filepath, temp_path)

        print(" - Splitting file into pages...")
        PDFBox.split_pages(temp_path)
        print(" - Finished splitting")

        print(" - Looking for split pages...")
        unmatched_time_cards = []
        duplicate_time_card_set = set()
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
                page = TimeCardPDFPage(text, original_filepath)
                if page.is_end_of_batch():
                    print(f"   - Detected END of BATCH page, discarding")
                elif page.is_2nd_page_time_card():
                    print(f"   - Detected 2nd page timecard, discarding")
                else:
                    page.verify_extracted_information()

                    # Allow revisions to overwrite an existing CC
                    if not is_revision:
                        # Check for a duplicate record that is the same name,date and invoice number and mark
                        duplicate_time_card_item = (
                            page.first_name,
                            page.last_name,
                            page.pay_period_month_string,
                            page.pay_period_day_string,
                            page.pay_period_year_string,
                            page.invoice_number
                        )
                        if duplicate_time_card_item in duplicate_time_card_set:
                            page.first_name = page.first_name + "_DUPLICATE_CC"
                            page.last_name = page.last_name + "_DUPLICATE_CC"
                            print(f'Detected duplicate!  Marking file: {page.output_file_name}')
                        else:
                            duplicate_time_card_set.add(duplicate_time_card_item)

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
                    tc.pay_period_month_string == cc.month and
                    tc.pay_period_day_string == cc.day and
                    tc.pay_period_year_string == cc.year and
                    tc.invoice_number == cc.invoice_number
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
                    PayrollProcess._cleanup_temp_files(cc_hash)

        # remove matches from unmatched lists
        for matched_tc in matched_time_cards:
            # print(f"Removing matched time card: {matched_tc.last_name} - {matched_tc.invoice_number}")
            unmatched_time_cards.remove(matched_tc)
        for matched_cc in matched_check_copies:
            # print(f"Removing matched check copy: {matched_cc.last_name}")
            unmatched_check_copies.remove(matched_cc)

        print("\nFinished.")
        print("\nThe following time cards were not matched to a check copy:")
        for time_card in sorted(unmatched_time_cards, key=lambda x: x.output_file_name):
            print(f" - {time_card.output_file_name}")

        print("\nThe following check copies were not matched to a time card:")
        for check_copy in sorted(unmatched_check_copies, key=lambda x: x.output_file_name):
            print(f" - {check_copy.output_file_name}")
