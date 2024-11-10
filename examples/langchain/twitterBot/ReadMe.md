Here’s a comprehensive **README.md** file for your Twitter bot project:

# Twitter Bot

This project is a Node.js Twitter bot that listens for tweets with the format `/ask @ReFiChat`, processes the query through a backend API, and replies with a concise answer. It stores tweet metadata and replies in a MongoDB database for tracking and management.

---

## Features

- Listens for tweets containing `/ask @ReFiChat`.
- Processes queries via a FastAPI backend.
- Posts replies to tweets with a concise answer and a link to the full response.
- Stores tweet metadata in MongoDB for auditing and catch-up replies.

---

## Prerequisites

1. **Node.js**: Install the latest LTS version from [Node.js official site](https://nodejs.org/).
2. **MongoDB**: Ensure MongoDB is installed and running. See [Setup MongoDB](#setup-mongodb).
3. **Twitter API Keys**: Set up a Twitter Developer account and generate API keys and access tokens.
4. **Environment Variables**: Create a `.env` file with the following variables:
   ```
   API_KEY=<Your Twitter API Key>
   API_SECRET=<Your Twitter API Secret>
   ACCESS_TOKEN=<Your Twitter Access Token>
   ACCESS_SECRET=<Your Twitter Access Secret>
   BEARER_TOKEN=<Your Twitter Bearer Token>
   ```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/twitter-bot.git
cd twitter-bot
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Setup MongoDB

Follow the steps below to install and configure MongoDB:

#### **Install MongoDB**
- **macOS**:
  ```bash
  brew tap mongodb/brew
  brew install mongodb-community
  brew services start mongodb/brew/mongodb-community
  ```
- **Ubuntu (Linux)**:
  ```bash
  wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | sudo apt-key add -
  echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -sc)/mongodb-org/5.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-5.0.list
  sudo apt-get update
  sudo apt-get install -y mongodb-org
  sudo systemctl start mongod
  sudo systemctl enable mongod
  ```
- **Windows**: Download and install MongoDB from [MongoDB Download Center](https://www.mongodb.com/try/download/community).

#### **Create Database and Collection**
MongoDB automatically creates the `twitterBotDb` database and `tweets` collection when the bot saves the first tweet. No manual setup is needed.

---

### 4. Configure the Bot User

For security, create a dedicated user for running the bot:

```bash
sudo adduser --shell /bin/bash twitterbotuser
sudo useradd -m -s /bin/bash twitterbotuser
sudo passwd twitterbotuser
sudo chown -R twitterbotuser:twitterbotuser /path/to/your/twitter-bot
sudo chmod -R 755 /path/to/your/twitter-bot
```

Update the systemd service file to run as this user (see [Running the Bot as a Service](#running-the-bot-as-a-service)).

---

### 5. Running the Bot

#### **Development Mode**
To run the bot in development mode:
```bash
node twitterBot.mjs
```

#### **Continuous Operation**
Use a process manager like `pm2` or `systemd` for continuous operation.

---

## Running the Bot as a Service

### Step 1: Create a Systemd Service File
Create a file at `/etc/systemd/system/twitter-bot.service` with the following content:

```ini
[Unit]
Description=Twitter Bot Service
After=network.target

[Service]
User=twitterbotuser
Group=twitterbotuser
WorkingDirectory=/path/to/your/twitter-bot
ExecStart=/usr/bin/node /path/to/your/twitter-bot/twitterBot.mjs
Restart=always
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
```

### Step 2: Enable and Start the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable twitter-bot
sudo systemctl start twitter-bot
sudo systemctl status twitter-bot
```

---

## Monitoring and Logs

### View Logs
- **With `pm2`**:
  ```bash
  pm2 logs twitter-bot
  ```
- **With `systemd`**:
  ```bash
  sudo journalctl -u twitter-bot -f
  ```

---

## Security Best Practices

- Run the bot as a non-root user (`twitterbotuser`).
- Store sensitive keys in the `.env` file and avoid hardcoding them in the code.
- Limit database and file permissions to the bot user.

---

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests to improve the bot.

---

## License

This project is licensed under the [MIT License](LICENSE).


---

### **Key Highlights of the README**

1. **Setup MongoDB**: Step-by-step instructions for macOS, Linux, and Windows.
2. **User Management**: Explains creating a dedicated user for security.
3. **Service Setup**: Describes using `systemd` for continuous operation.
4. **Environment Variables**: Details `.env` setup for sensitive data.
5. **Logs and Monitoring**: Explains how to track logs.

Let me know if you’d like modifications or additional sections!
