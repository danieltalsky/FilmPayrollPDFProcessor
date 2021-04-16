# Command line tools for PDFBOX
# https://pdfbox.apache.org/2.0/commandline.html

# Split a PDF into dash-numbered files
docker-compose run pdf PDFSplit /home/pdfs/WE_031321_817_TEAMSTERS.pdf

# Extract text from split file into console
docker-compose run pdf ExtractText /home/pdfs/WE_031321_817_TEAMSTERS-1.pdf -console true