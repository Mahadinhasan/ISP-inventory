# ISP Inventory Management System

A comprehensive, real-time inventory and workflow management system built with Django and Django Channels (WebSockets). This system is designed specifically for ISP (Internet Service Provider) operations to manage materials, track usage across multiple branches, and facilitate seamless internal communication.

## 🚀 Key Features

*   **Real-Time Monitoring**: Live tracking of branch stock, online presence, and system activity using WebSockets.
*   **Role-Based Access Control (RBAC)**: Strict permission enforcement tailored for Admin, Storekeeper, NOC, and Branch users.
*   **Material Workflow**: Complete lifecycle tracking from requisition to approval, dispatch, branch reception, and client usage.
*   **Serialized Inventory**: Advanced tracking for MAC/Serial numbered devices.
*   **Automated Monthly Processing**: Auto-reset of branch stock limits and automated archiving at month-end.
*   **Internal Communication**: Real-time one-to-one chat and online presence tracking.
*   **Analytics & Reporting**: Comprehensive dashboard analytics with one-click Excel and PDF report exports.
*   **Damage & Refunds**: Dedicated workflows for handling damaged and refundable materials.

## 👥 User Roles & Capabilities

The system operates on four distinct user roles, each with specialized capabilities:

### 1. Admin
*   Full system control and configuration.
*   Approves material requests from Branch users.
*   Access to the **Live Materials Monitoring** dashboard to track real-time stock across all branches.
*   Manages users, roles, and system backups.
*   Full access to detailed analytics and reports.

### 2. Storekeeper
*   Manages the central inventory (adds, edits, categorizes materials).
*   Executes the physical dispatch (Pass On) of materials after Admin approval.
*   Monitors overall warehouse stock levels (Normal, Low Stock, Out of Stock).
*   Handles damaged material verifications.

### 3. NOC (Network Operations Center)
*   Manages specialized tasks and network operations.
*   Can add serialized/MAC-based materials directly.
*   Directly assigns materials to branches (bypassing the standard Storekeeper workflow).
*   Real-time presence monitoring to assign urgent tasks to online branches.

### 4. Branch (Technicians)
*   Submits material requisition requests to the Admin.
*   Receives dispatched materials into their local stock.
*   Logs material usage against specific clients or POPs (Point of Presence).
*   Reports damaged materials and handles refundable (re-usable) items.
*   Maintains a personalized dashboard of their current usable stock.

## 🛠️ Technical Stack & Architecture

*   **Backend Framework**: Django (Python)
*   **Real-Time Engine**: Django Channels (ASGI), Redis (Channel Layer)
*   **Database**: SQLite / PostgreSQL
*   **Frontend**: HTML5, Vanilla CSS / Tailwind CSS, JavaScript (Vanilla JS for WebSocket and DOM manipulation)
*   **Reporting**: Excel (OpenPyXL / XlsxWriter), PDF generation integrations.

### WebSocket (Live) Integration
The system heavily utilizes Django Channels to provide real-time updates without page reloads:
*   **Live Monitoring**: Admin dashboards instantly reflect stock changes when a branch user consumes or receives a material.
*   **Presence Tracking**: Users' online/offline statuses are broadcasted globally.
*   **Internal Chat**: Secure, real-time messaging between system users.
*   **Push Notifications**: Instant alerts for material approvals, rejections, and low stock warnings.

## ⚙️ Setup & Installation

1. **Clone the Repository**
   ```bash
   git clone <repository_url>
   cd ISP-inventory/ibccl
   ```

2. **Set up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file in the root directory and configure necessary variables (Database, Secret Key, etc.).

5. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create Superuser (Admin)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the Development Server**
   To support WebSockets, the application must be run using an ASGI server (like Daphne) or Django's built-in runserver (if Channels is properly configured).
   ```bash
   python manage.py runserver
   ```
   *Note: Ensure Redis is installed and running if you are using the Redis channel layer for WebSockets.*

## 🔒 Security Highlights
*   **Session Management**: Configurable session timeouts (e.g., 24-hour persistence or browser-close expiry).
*   **JWT / Token Auth**: Future-proofed API architecture for potential mobile app integrations.
*   **Strict Query Filtering**: Users only access data relevant to their role and branch.

---
*Built with ❤️ for efficient ISP operations and inventory management.*
