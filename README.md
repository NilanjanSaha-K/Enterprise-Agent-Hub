Enterprise Agent Hub 🤖

A production-grade AI Agent platform designed for workforce analytics, HR support, and document intelligence. Built with **React**, **Python Flask**, and **Google Cloud**.

🚀 Features

* **Role-Based Access Control (RBAC):** Distinct interfaces for Admins, Employees, and Public users.
* **RAG Knowledge Base:** Admins can upload PDFs to train the AI instantly using **ChromaDB**.
* **Analytics Agent:** Converts natural language queries (e.g., "Compare Apple vs Microsoft") into live graphs and CSV exports using **Matplotlib** and **Pandas**.
* **Persistent Chat:** History saved to **Firebase Firestore** with context-aware recall.
* **Google Integration:** One-click export to **Google Docs** and **Sheets**.

🛠️ Tech Stack

* **Frontend:** React (Vite), Tailwind CSS, Lucide Icons, Firebase Auth.
* **Backend:** Python Flask, LangChain, Google Gemini Pro, Gunicorn.
* **Database:** Firebase Firestore (NoSQL) & ChromaDB (Vector).
* **Infrastructure:** Google Cloud Run (Backend Hosting) & Firebase Hosting (Frontend).

📦 Installation

1.  Clone the repo:
    ```bash
    git clone [https://github.com/NilanjanSaha-K/Enterprise-Agent-Hub.git](https://github.com/NilanjanSaha-K/Enterprise-Agent-Hub.git)
    ```
2.  Install Backend Dependencies:
    ```bash
    cd backend
    pip install -r requirements.txt
    ```
3.  Install Frontend Dependencies:
    ```bash
    cd frontend
    npm install
    ```
4.  Setup Environment:
    * Create a `.env` file in `backend/` with your Google Cloud & Firebase keys.
    * Add your `service_account.json` (not included for security).

## 🛡️ License

This project is for educational and portfolio purposes.
