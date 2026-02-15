# ZENO_SMM
This is a Advanced Zeno_Smm panel🚀 telegram Bot Resporatory which helps to make a smm panel bot from the other smm panel website's api url and api🌐
_________________________________________

#README.md FILE
_________________________________________
# 💎 SMM Panel Telegram Bot

A fully-featured SMM (Social Media Marketing) Panel bot for Telegram with dual-server support, automated payments, and comprehensive admin controls.

## 🌟 Features

### 📱 User Features
- **Dual Server System**
  - Server 1: Fixed provider with refund support
  - Server 2: Configurable provider (no refund)
  - Server selection on startup with inline buttons
  
- **Service Management**
  - Browse services by categories
  - Advanced search functionality
  - Direct order placement
  - Real-time order tracking
  - Order history with server info

- **Payment System**
  - UPI QR code generation with exact amount
  - Manual payment verification
  - Screenshot + UTR submission
  - Real-time balance updates
  - Payment approval/rejection notifications

- **Order Management**
  - Place orders with service ID
  - Cancel pending orders (Server 1 only)
  - Request refunds (Server 1 only)
  - Auto-refund on order cancellation
  - Order status notifications

- **Support System**
  - Direct messaging to admin
  - Photo sharing support
  - Admin reply functionality

### 👨‍💼 Admin Features

- **Server Management**
  - Configure Server 2 dynamically
  - Format: `url|api_key|markup`
  - Enable/disable Server 2
  - Independent server caching

- **Payment Management**
  - Approve/reject deposits via payment group
  - Set UPI ID
  - View deposit requests with screenshots
  - Manual balance adjustment

- **User Management**
  - View user statistics
  - Ban/unban users
  - Add/deduct/set user balance
  - View all orders

- **Refund Management**
  - Approve/reject refund requests
  - Automatic refund processing
  - Manual refund option
  - Refund notifications

- **Broadcasting**
  - Text messages
  - Photo broadcasts
  - Inline button support
  - Success/failure statistics

- **Channel Management**
  - Add multiple force-join channels
  - Remove channels
  - Dynamic channel verification

- **Bot Controls**
  - Enable/disable bot
  - Notify all users on status change
  - Admin panel with inline keyboard

## 🚀 Installation

### Prerequisites
```bash
Python 3.8+
pip (Python package manager)
```

### Required Packages
```bash
pip install python-telegram-bot requests --break-system-packages
```

### Setup Steps

1. **Clone/Download the bot file**
```bash
# Download smm_panel_bot_final.py
```

2. **Configure Bot Token**
```python
# Edit in the file
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = YOUR_TELEGRAM_USER_ID
```

3. **Configure Server 1 (Fixed)**
```python
SERVER1_API_URL = "https://your-smm-provider.com/api/v2"
SERVER1_API_KEY = "your_api_key_here"
SERVER1_MARKUP = 5  # Markup in rupees
```

4. **Configure Payment Group**
```python
PAYMENT_GROUP = "@your_payment_group"
```

5. **Set Force Join Channel**
```python
FORCE_CHANNEL = "@your_channel"
```

6. **Run the Bot**
```bash
python3 smm_panel_bot_final.py
```

## 📋 Configuration

### Bot Settings
| Setting | Description | Default |
|---------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | Required |
| `ADMIN_ID` | Your Telegram user ID | Required |
| `FORCE_CHANNEL` | Channel username for force join | @nomethod0 |
| `PAYMENT_GROUP` | Group for payment approvals | @payment_gd18 |

### Server 1 Settings (Fixed)
| Setting | Description | Default |
|---------|-------------|---------|
| `SERVER1_API_URL` | SMM panel API endpoint | Required |
| `SERVER1_API_KEY` | API key for authentication | Required |
| `SERVER1_MARKUP` | Markup amount in ₹ | 5 |

### Server 2 Settings (Dynamic)
Configure via Admin Panel:
- API URL
- API Key
- Markup
- Enable/Disable

## 🎯 Usage

### For Users

1. **Start Bot**
   ```
   /start
   ```
   - Join required channels
   - Select server (Server 1 or Server 2)

2. **Place Order**
   - Click "🛒 New Order"
   - Enter service ID
   - Enter link/username
   - Enter quantity
   - Confirm order

3. **Search Services**
   - Click "📂 Categories"
   - Click "🔍 Search Service"
   - Enter keywords (e.g., "Instagram followers")
   - Click "🛒 Order" button on results

4. **Add Funds**
   - Click "💳 Add Funds"
   - Enter amount (minimum ₹10)
   - Scan QR code and pay
   - Send payment screenshot
   - Enter 12-digit UTR
   - Wait for approval

5. **Cancel Order** (Server 1 only)
   - Go to "📦 Order History"
   - Click "❌ Cancel" on pending order
   - Automatic refund if successful

### For Admin

1. **Access Admin Panel**
   ```
   /admin
   ```

2. **Configure Server 2**
   - Click "🖥️ Configure Server 2"
   - Send: `https://api.example.com/v2|your_api_key|10`
   - Server 2 enabled automatically

3. **Approve Payments**
   - Check payment group for requests
   - Click "✅ Approve" or "❌ Reject"
   - User gets instant notification

4. **Manage Refunds**
   - Click "💵 Refund Requests"
   - Click "✅ Approve" on order ID
   - Refund processed automatically

5. **Broadcast Message**
   - Click "📢 Broadcast"
   - Send text message
   - Add photo (optional)
   - Add button (optional)
   - View success/failure stats

6. **Manage Users**
   - Click "💰 Manage Balance"
   - Enter user ID
   - Add/Deduct/Set amount
   - User notified automatically

## 📊 Categories

Available service categories:
- 🔍 Search Service
- 👥 Telegram Members
- 👁 Telegram Views
- 🔮 Telegram Views [Future]
- 📌 Telegram Views [Last Post]
- ❤️ Telegram Reaction
- 📸 Instagram Followers
- 👀 Instagram Views
- 💗 Instagram Likes

## 🔧 Admin Commands

### Via Admin Panel (`/admin`)

| Button | Function |
|--------|----------|
| ⚙️ Set UPI | Configure UPI ID for payments |
| 💵 Refund Requests | View and approve refunds |
| 📊 All Orders | View order statistics |
| 👥 User Stats | View user statistics |
| 💰 Manage Balance | Add/deduct user balance |
| 🚫 Ban/Unban User | Ban or unban users |
| 🤖 Bot ON/OFF | Enable/disable bot |
| 📢 Broadcast | Send messages to all users |
| 📢 Add Channel | Add/remove force join channels |
| 🖥️ Configure Server 2 | Setup Server 2 provider |

## 💳 Payment Flow

```
User                    Bot                     Admin
  |                      |                        |
  |--Enter Amount------->|                        |
  |                      |--Generate QR---------->|
  |<-----QR Code---------|                        |
  |                      |                        |
  |--Send Screenshot---->|                        |
  |--Send UTR----------->|                        |
  |                      |--Forward to Group----->|
  |                      |                        |
  |                      |<--Approve/Reject-------|
  |<--Notification-------|                        |
  |                      |                        |
```

## 🔄 Order Flow

```
User                    Bot                     SMM API
  |                      |                        |
  |--Place Order-------->|                        |
  |                      |--Check Balance-------->|
  |                      |--Deduct Balance------->|
  |                      |--Submit Order--------->|
  |<--Order Confirmation-|<--Order ID-------------|
  |                      |                        |
  |                      |--Check Status--------->|
  |<--Status Update------|<--Order Complete-------|
  |                      |                        |
```

## 📁 File Structure

```
smm_panel_bot_final.py    # Main bot file
smm_panel_data.json       # Auto-generated data file
README.md                 # This file
```

## 🗄️ Data Storage

All data stored in `smm_panel_data.json`:
- User balances
- Order history
- Deposit records
- Refund requests
- Server configurations
- Services cache
- Bot settings

## ⚡ Performance Features

- **Service Caching**: 2-hour cache for both servers
- **Async Operations**: Non-blocking order processing
- **Batch Broadcasting**: 0.05s delay between messages
- **Optimized Queries**: Minimal API calls
- **Error Handling**: Graceful fallbacks

## 🔒 Security Features

- **Admin-only commands**: Restricted access
- **User verification**: Force channel join
- **Ban system**: Block malicious users
- **UTR validation**: 12-digit verification
- **Payment verification**: Screenshot + UTR required
- **API key protection**: Secure storage

## 🐛 Troubleshooting

### Common Issues

**1. Search not working**
- Ensure server is selected via `/start`
- Check if service cache is updated
- Verify API connectivity

**2. QR code showing wrong amount**
- Check UPI ID in admin panel
- Verify amount is properly entered
- Test with different amounts

**3. Orders not processing**
- Check API credentials
- Verify service ID exists
- Check user balance

**4. Bot not responding**
- Check bot token
- Verify Python version (3.8+)
- Check internet connection

**5. Payment not approved**
- Check payment group settings
- Verify admin access
- Check screenshot upload

## 📝 Changelog

### Version 2.0 (Current)
- ✅ Added dual-server system
- ✅ Server 2 dynamic configuration
- ✅ Welcome message with server selection
- ✅ Fixed search functionality
- ✅ Fixed QR code amount generation
- ✅ Photo broadcast support
- ✅ Improved error handling
- ✅ Better UPI link encoding

### Version 1.0
- Initial release
- Single server support
- Basic order management
- Manual payment system

## 🤝 Support

For support and updates:
- Telegram: @ffzeno18
- Channel: @nomethod0

## ⚠️ Important Notes

1. **Server 1 (Fixed)**:
   - Never changes
   - Supports refunds
   - Recommended for new users

2. **Server 2 (Dynamic)**:
   - Can be changed anytime
   - No refund support
   - Admin configurable

3. **Refund Policy**:
   - Server 1: Refunds available
   - Server 2: No refunds
   - Auto-refund on cancellation (Server 1)

4. **Payment Processing**:
   - Manual approval required
   - 5-10 minute processing time
   - UTR must be 12 digits

5. **Balance Management**:
   - Preserved across server changes
   - Admin can adjust manually
   - Auto-deduct on orders

## 📜 License

This bot is provided as-is for educational and commercial use.

## 🙏 Credits

- Developed by: @ffzeno18
- Powered by: python-telegram-bot
- QR Generation: api.qrserver.com

---

**Made with ❤️ for SMM Panel Management**

For any issues or feature requests, contact @ffzeno18 on telegram
