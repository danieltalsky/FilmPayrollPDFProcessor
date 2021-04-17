import os

from film_payroll_pdf_processor.payroll_process import (
    PayrollProcess,
    INBOX_FOLDER_PATH,
)


def main():
    """
    Iterates through pdfs in the PDF Inbox, processing check copies and time cards
    """

    unmatched_time_cards = []
    unmatched_check_copies = []

    # First pass, do all
    for filename in os.listdir(INBOX_FOLDER_PATH):
        # File Type Detection
        if filename.endswith(".pdf") and filename.startswith("WE_") and "REVISED" not in filename:
            print(f"\nDetected TimeCards file for processing: {filename}")
            unmatched_time_cards = unmatched_time_cards + \
                PayrollProcess.process_multi_page_time_card(
                    os.path.join(INBOX_FOLDER_PATH, filename)
                )
        elif filename.endswith(".pdf") and not filename.startswith("WE_"):
            print(f"\nDetected PDF file for processing, processing as Check Copies package: {filename}")
            unmatched_check_copies = unmatched_check_copies + \
                PayrollProcess.process_multi_page_check_copies_package(
                    os.path.join(INBOX_FOLDER_PATH, filename)
                )
        elif filename.endswith(".txt") or filename == ".gitkeep" or "REVISED" in filename:
            # Text files are picked up with their PDFs
            # Revisions handled in second pass
            # .gitkeep should be ignored
            pass
        else:
            print(f"\nSKIPPING: File found but not identified: {filename}")

    # Revision pass
    # First pass, do only revisions
    revised_time_cards = []
    for filename in os.listdir(INBOX_FOLDER_PATH):
        if filename.endswith(".pdf") and filename.startswith("WE_") and "REVISED" in filename:
            print(f"\nDetected *Revised* TimeCards file for processing: {filename}")
            revised_time_cards = revised_time_cards + \
                PayrollProcess.process_multi_page_time_card(
                    os.path.join(INBOX_FOLDER_PATH, filename), is_revision=True
                )

    print(f"\nFiles written:")
    print(f" - wrote {len(unmatched_time_cards)} time cards")
    print(f" - wrote {len(revised_time_cards)} check copies REVISIONS")
    print(f" - wrote {len(unmatched_check_copies)} check copies")
    PayrollProcess.match_time_cards_to_check_copies(
        unmatched_time_cards,
        unmatched_check_copies
    )


if __name__ == '__main__':
    main()
