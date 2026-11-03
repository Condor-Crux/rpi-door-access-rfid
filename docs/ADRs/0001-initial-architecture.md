# ADR 0001: Initial Architecture Decisions

## Status
Accepted

## Context
We are bootstrapping a localized IoT application on a Raspberry Pi using Python to manage a door via an RFID reader. The system must be robust, extensible, and scalable for future integrations like AWS IoT. The system needs local hardware state management and an internal web UI.

## Decisions

### 1. Use Python and FastAPI
**Decision:** We will use **Python** for core logic, and **FastAPI** as the framework for the Web Interface and API.
**Reason:** 
- Python is standard for Raspberry Pi hardware bridging (`GPIO`/`gpiozero`).
- FastAPI natively provides an async and high-performance API ecosystem while also easily serving static single-page Web UIs. This satisfies the requirement of having both a web view and an API.

### 2. SQLite for Local Data Storage
**Decision:** We will use **SQLite**.
**Reason:** 
- It is local, serverless, and does not demand heavy external binaries for the RPi.
- Suitable for the three required structures: Users/Credits, Access Logs, and Count/Limit Tracking.

### 3. Strict SOLID - Open/Closed Principle
**Decision:** The hardware logic will be injected and abstracted.
**Reason:**
- The domain layer evaluating the access and credits should not inherently know it is running on a Raspberry Pi.
- We will use Dependency Injection. Interfaces like `LedController`, `BuzzerController`, `RelayController`, and `RFIDScanner` will be defined. The physical implementations using Pi GPIO modules will be injected at runtime.
- If we change the LED board or move from local GPIO to I2C, none of the access domain logic must change.

### 4. Code Dryness
**Decision:** Ensure DRY practices.
**Reason:**
- Reusable utilities for the SQLite connections, Logging formats, and GPIO pin lifecycle management will be created rather than sprawling raw code across multiple endpoints and business logic areas.
