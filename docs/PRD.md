# Product Requirements Document (PRD)

## Overview
IoT application for a Raspberry Pi designed to manage a door access system using RFID. The system is paired with local hardware for visual/audio feedback and physical unlocking, and exposes a web interface and API for management. 

## Hardware Requirements
- Raspberry Pi (running Linux/Raspbian OS)
- RFID Card Reader
- Sound Buzzer
- Red LED
- Green LED
- 5V Relay (controls the door lock)

## Software Components
- **Language:** Python
- **API and UI Backend:** FastAPI
- **Databases:** SQLite (embedded local DB handling Accounts, Users, Companies, Logs)

## System Workflows

### 1. Door Access Validation Flow
1. **Trigger:** The system reads an RFID card access swipe.
2. **Account Validation (Private DB):**
   - The system checks an embedded private SQLite database for the scanned ID (`Account`).
   - The `Account` is tied to a `User` (first and last name, email) who belongs to a `Company`.
   - If **Found**:
     - Check the `account_status` column. Must be Active.
     - Check the `expiration_date` column. Must not be expired.
3. **Credit Validation Engine (Credits DB / Same DB):**
   - Check the `Credits` column on the ID.
   - If Credits > 0 and all previous conditions are verified:
     - **Access Granted Sequence:**
       - Log "Access Granted" in a dedicated log database.
       - Activate Green LED.
       - Emit 1 positive Beep.
       - Decrement the `Credits` count by 1.
       - Add an entry (ID, timestamp) into the limit tracking DB to count historical usage or handle limits.
       - Trigger the 5V Relay for 5 seconds to unlock the door.
   - If Credits == 0 (Out of Credits):
     - **Denial Sequence:**
       - Emit 3 error Beeps.
       - Activate Red LED.
       - Keep door locked.
4. **General Error Flow (Not Found / Expired / Invalid Status):**
   - **Denial Sequence:**
     - Emit standard error beep (differing from the out-of-credit beep).
     - Activate Red LED.
     - Keep door locked.

### 2. Web UI & Configuration
- **FastAPI-powered Application:**
   - Serves a simple local dashboard (`http://localhost`) providing CRUD capabilities.
   - Allows loading and managing RFID IDs.
   - Allows users to recharge, edit credits, modify expiration dates, and activate/deactivate statuses.
   - Allows managing Users and Companies and linking multiple RFIDs to a single User.
   - Exposes a RESTful API layer out of the box because of FastAPI usage.
 
### 3. AWS Synchronization
- The system will sync data to AWS. 
- In later phases, every access will be annotated and pushed via AWS IoT Core.
