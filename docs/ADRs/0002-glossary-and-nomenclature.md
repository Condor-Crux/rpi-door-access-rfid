# ADR 0002: Naming Conventions and Glossary (SSOT)

## Status
Accepted

## Context
To maintain consistency across this repository, we must align on a Single Source of Truth (SSOT) for all domain entities, variables, functions, and colloquial terms. Everything down to the code layer must use these exact terms to prevent ambiguity.

All code (variables, classes, functions) **MUST** be written in **English**. 
Colloquial terminology will map between the concepts in English code and the real-world Spanish context.

## 1. Domain Entities & Database Nomenclatures

| English Code Entity | Spanish Colloquial | Definition |
| :--- | :--- | :--- |
| `Company` / `CompanyModel` | Empresa | The entity representing a company. |
| `User` / `UserModel` | Usuario | The entity representing a person. Associated to a Company. Can have multiple Accounts. |
| `Account` / `AccountModel` | Cuenta / Tarjeta | The entity representing an access card. Stored in SQLite. Belongs to a User (`user_id`). |
| `AccessLog` | Log de Acceso / Historial | The entity tracking each time a card is scanned, granted, or denied. |
| `CreditCount` | Límite de Usos / Créditos | The remaining valid accesses an `Account` has. |
| `RFIDCard` / `CardID` | Tarjeta / Llavero RFID | The physical object scanned by the reader. Its UID is the primary identifier. |

## 2. Hardware Interfaces Nomenclatures

Any abstraction representing hardware must follow this naming convention:
- **`RFIDReader`**: Not *scanner*, not *sensor*. 
- **`DoorRelay`**: Not *lock*, not *apertura*. It controls the 5V relay.
- **`Buzzer`**: The alarm/sound component.
- **`LedIndicator`**: The component handling LEDs. Specific instances must be `red_led` and `green_led`.

## 3. Variable and Property Standards

For precise database schemas and domain code properties, use these exact terms:

- `account_id` (string): The UID of the `RFIDCard`.
- `status` (string): Current state of the account. Must be exactly `"active"` or `"inactive"`. (Colloquial: *estado*).
- `expiration_date` (datetime): The boundary for validity. (Colloquial: *fecha de vencimiento*).
- `credits` (integer): Remaining accesses. (Colloquial: *créditos*).
- `timestamp` (datetime): When an event occurs.

## 4. Workflows and Functions Nomenclatures

Verbs used in code to define the Access Flow:
- `process_swipe(card_id)`: The main entry point when a card is tapped.
- `validate_account(card_id)`: Checks `status` and `expiration_date`.
- `validate_credits(card_id)`: Checks if `credits` > 0.
- `grant_access()`: Emits 1 positive beep on `Buzzer`, lights `green_led`, decreases `credits`, logs success, triggers `DoorRelay`.
- `deny_access(reason)`: Emits 3 error beeps (if no credit) or 1 error beep (other), lights `red_led`, logs failure.

## Enforcement
This ADR must be updated BEFORE any new domain concept or hardware piece is introduced. Agents interacting with the codebase must strictly cross-reference variables against this SSOT.
