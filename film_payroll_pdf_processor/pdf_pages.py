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


class TimeCardPDFPage(PDFPage):
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