# Film Payroll PDF Processor

Uses Apache PDFBox, Python, and Docker to process payroll documents.

## Week setup:

- Place time card files for a specific week beginning with `WE_` in `pdfs/inbox`
- Place check copy files for a specific week in `pdfs/inbox`
- Create `.txt` files for all check copy files

## Running:

- Ensure Docker is installed and running
- Run `docker-compose run pdf`