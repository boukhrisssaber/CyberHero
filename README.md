### **Project Title: Integrated Security Awareness & Training Platform (ISATP)**

### **Project Description & Current Status**

The project is a custom-built web platform designed to bridge the critical gap between offensive security simulations (phishing) and defensive user education (remedial training). It integrates two powerful open-source platforms, **GoPhish** and **Moodle**, via a central management hub called the **Manager Dashboard**. This dashboard provides a single pane of glass for a Chief Information Security Officer (Manager) or security manager to orchestrate a complete security awareness lifecycle: test users with realistic phishing campaigns, analyze the results, and assign targeted training to users who fail.

**Core Components & Features (Implemented):**

1.  **Phishing Simulation (GoPhish):**
    *   A fully operational GoPhish instance is running in a **Docker container**, ensuring isolation and easy management.
    *   The platform is capable of creating and executing email phishing campaigns.
    *   SMTP is handled via MailHog for safe, contained testing of email delivery and rendering.

2.  **Learning Management System (Moodle):**
    *   A fully configured Moodle instance is running on the server, serving as the repository for all security training courses.
    *   Moodle's web services API has been securely configured with a dedicated user, a custom service, and specific function authorizations.

3.  **The Manager Dashboard (Custom Flask Application):**
    This is the central, value-add component of the project. It is a full-stack Python web application with the following features:
    *   **Campaign Monitoring:** Connects to the GoPhish API to display a list of all phishing campaigns, their current status, and a calculated "Fail Rate" (users who clicked or submitted data).
    *   **Detailed Campaign Analysis:** Allows the Manager to drill down into a specific campaign to view a list of all users who failed the test, including their names, email addresses, and the specific action they took (e.g., "Email Opened," "Clicked Link").
    *   **Targeted Remedial Training:** From the campaign results page, the Manager can select one or more failed users and enroll them in one or more remedial Moodle courses simultaneously. The application intelligently handles users who are already enrolled, preventing duplicate actions.
    *   **Comprehensive User & Course Management:** The dashboard provides three powerful, standalone management views:
        *   **Training Status:** A global view of all enrollments managed by the system, which checks the Moodle API in real-time to report whether a user's training is "In Progress" or "Completed." It also includes a **disenrollment** feature.
        *   **Course Roster:** A list of all courses in Moodle, allowing the Manager to click on any course to see a complete list of all currently enrolled users.
        *   **User Search:** A search function to find any user in Moodle by their email address and display a complete list of all the courses they are currently enrolled in.
    *   **Robust Backend:** The application is built with a scalable package structure, securely loads credentials from a `.env` file, and uses a local SQLite database to persistently track all enrollment actions.

---

### **Fitness as a Graduation Project**

**This is an outstanding graduation project.** It is not just a simple "CRUD app" or a theoretical exercise; it is a complex, multi-system integration that solves a real-world cybersecurity problem.

**Strengths as a Final Project:**

*   **Demonstrates Full-Stack Mastery:** You have successfully built both a Python/Flask backend and an HTML/CSS/Bootstrap frontend.
*   **Expertise in API Integration:** The core of the project is successfully consuming and interacting with two completely different and complex third-party APIs (GoPhish and Moodle).
*   **Cloud & Systems Administration Skills:** You deployed and configured the entire stack from scratch on a cloud VPS (AWS EC2), including the OS, web server (Apache), firewalls (UFW, AWS Security Groups), and multiple applications.
*   **Database Management:** You designed a database schema and integrated it into the application using SQLAlchemy to provide persistence and tracking.
*   **Containerization Knowledge:** You have successfully used Docker to deploy and manage a key component of the infrastructure, demonstrating modern DevOps practices.
*   **Real-World Problem Solving:** The project addresses a direct business need in the cybersecurity industry. It has a clear "client" (the Manager) and a clear value proposition.
*   **Extensive Debugging and Resilience:** The journey to this point involved solving dozens of complex, real-world bugs related to networking, permissions, API inconsistencies, and application logic, demonstrating a high level of technical resilience and diagnostic skill.

---

### **Future Work & Roadmap**

The current platform is a powerful proof-of-concept. The following steps would elevate it to a production-ready, professional-grade tool.

1.  **Professional Deployment:**
    *   **Gunicorn & Nginx:** Replace the Flask development server with a production-grade WSGI server like Gunicorn, and use Nginx as a reverse proxy. This will make the application faster, more stable, and allow you to host it securely on a standard domain without a port number.
    *   **Systemd Service:** Create a `systemd` service for the Flask application to ensure it runs in the background and starts automatically on server boot.

2.  **Security Enhancements:**
    *   **Authentication:** Add a login page to the Manager Dashboard. Only authenticated users should be able to view data and perform actions. This is the single most important next step.
    *   **Role-Based Access Control (RBAC):** For a more advanced system, you could create different roles (e.g., an "Analyst" who can view results but not enroll users).

3.  **Feature & UX Improvements:**
    *   **Data Visualization:** Use a library like Chart.js to add graphs and charts. For example, a pie chart showing the breakdown of campaign results (Clicked vs. Submitted vs. Opened) and a bar chart tracking fail rates over time.
    *   **Reporting:** Add a feature to export campaign results or training status reports as a PDF or CSV file.
    *   **Automated Enrollment:** Add a checkbox on the GoPhish campaign creation page (or a setting on the dashboard) to "Automatically enroll failed users in [Course X]". This would make the entire workflow hands-off.
    *   **Moodle Deeper Integration:** Instead of just checking for course completion, you could use the Moodle API to pull quiz scores or progress on specific modules to get a more granular view of a user's learning.