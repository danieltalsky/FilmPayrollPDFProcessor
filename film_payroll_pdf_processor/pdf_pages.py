import re


class PDFPage:
    pass


class CheckCopyPDFPage(PDFPage):

    month: str
    day: str
    year: str
    page_number: str
    payee_last_name: str
    payee_first_name: str
    invoice_number: str

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
    ):
        self.month = month
        self.day = day
        self.year = year
        self.page_number = page_number
        self.payee_last_name = payee_last_name
        self.payee_first_name = payee_first_name
        self.invoice_number = invoice_number

    @property
    def output_file_name(self):
        # Format: "CC-Last,First-031321-ECY879-74039.00.pdf"
        first_name = self.payee_first_name
        last_name = self.payee_last_name
        month = self.month
        day = self.day
        year = self.year
        invoice = self.invoice_number
        return f"CC-{last_name},{first_name}-{month}{day}{year}-{invoice}.pdf"

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


class TimeCardPDFPage(PDFPage):
    """
    Models the important data in a split time card PDF page
    """

    END_OF_BATCH_INDICATOR = "END of BATCH"

    raw_page_text: str = None

    first_name: str = None
    last_name: str = None
    pay_period_day_string: str = None
    pay_period_month_string: str = None
    pay_period_year_string: str = None
    invoice_number: str = None

    def __init__(self, raw_page_text, original_filepath):
        self.raw_page_text = raw_page_text
        self.original_filepath = original_filepath
        self.extract_name()
        self.extract_pay_period_date()
        self.extract_invoice_number()

    def verify_extracted_information(self):
        missing_information = []
        if not self.first_name or not self.last_name:
            missing_information.append("Payee name")
        if not self.pay_period_month_string or not self.pay_period_day_string or not self.pay_period_year_string:
            missing_information.append("Pay period ending date")
        if not self.invoice_number:
            missing_information.append("Invoice Number")
        if len(missing_information):
            missing = ", ".join(missing_information)
            error = f"\n\nERROR: Couldn't get the following information from this file: "
            error += self.original_filepath
            error += f"{missing}"
            error += "Extracted text from the PDF for troubleshooting:"
            error += f"\n -------- \n {self.raw_page_text} \n ------- \n"
            raise Exception(error)

    def is_2nd_page_time_card(self) -> bool:
        """
        Checks in a PDF time card page to see if the page is a 2nd page time card and should be discarded

        :return:
        """
        return "Grand Total:" not in self.raw_page_text

    def is_end_of_batch(self) -> bool:
        """
        Checks in a PDF time card page to see if the page is an "end of batch" placeholder page

        :return:
        """
        return self.END_OF_BATCH_INDICATOR in self.raw_page_text

    @property
    def output_file_name(self):
        # Format: "TC-Last,First-031321-BBB123.pdf"
        first_name = self.first_name
        last_name = self.last_name
        day = self.pay_period_day_string
        month = self.pay_period_month_string
        year = self.pay_period_year_string
        invoice_number = self.invoice_number
        return f"TC-{last_name},{first_name}-{month}{day}{year}-{invoice_number}.pdf"

    def extract_invoice_number(self):
        """
        Looks for an invoice number surrounded by underscores in the filename

        Example:
            pdfs/inbox/WE_041021_EYY896_CONSTRUCTION (2).pdf
            =
            _EYY896_
            =
            EYY896
        """
        # print(self.original_filepath)
        match = re.search(
            r"_[A-Z]{3}[0-9]{3}_",
            self.original_filepath
        )
        if match:
            invoice_number = match.group()
            invoice_number = invoice_number.replace("_", "")
            self.invoice_number = invoice_number

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
