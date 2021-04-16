import os

from film_payroll_pdf_processor.payroll_process import (
    PayrollProcess,
    INBOX_FOLDER_PATH,
)


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


if __name__ == '__main__':
    main()
