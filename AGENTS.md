# Sample AGENTS.md file
	
## Project context
This is a modern Python IoT App for Raspberry Pi managing an RFID door.
We use FastAPI (providing both Web UI and a REST API) and SQLite.

## Code Guidelines
- **Strict SOLID:** Particularly Open/Closed Principle. Abstract external hardware (Relays, LEDs, Buzzers, RFID scanners) behind interfaces.
- **DRY:** Don't repeat yourself.
- **Framework:** FastAPI for backend API / Web server.

## Relevant documentation
- Product requirements: `/docs/PRD.md`
- Architecture Decisions: `/docs/ADRs/`
