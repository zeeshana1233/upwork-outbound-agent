# Channel IDs — Upwork_Bot server (server_id=1277527228401319936)
# #appilot          1359407667692572713  → Android Automation
# #stealth-mode     1359040879121403965  → Stealth Automation
# #ai-automation    1372474025476882532  → AI Automation
# #web-dev          1364551909251223594  → Web Development
# #tiktok-shop      1371453441938817054  → TikTok Shop
# #automation       1359040738507358340  → General Automation

ADVANCED_JOB_SEARCHES = [
    # ─── ANDROID AUTOMATION ──────────────────────────────────────────────────
    # Channel: #appilot
    # contractor_tier: ["2","3"]  Intermediate + Expert
    {
        "category": "Android Automation",
        "keyword": "Mobile Farm",
        "query": "Mobile farm",
        "channel_id": 1359407667692572713,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Android Automation",
        "keyword": "Appium",
        "query": "Appium",
        "channel_id": 1359407667692572713,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Android Automation",
        "keyword": "iPhone Automation",
        "query": "Iphone Automation",
        "channel_id": 1359407667692572713,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Android Automation",
        "keyword": "Mobile Bot",
        "query": "title:(Mobile bot)",
        "channel_id": 1359407667692572713,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Android Automation",
        "keyword": "Phone Farm",
        "query": "phone AND farm",
        "channel_id": 1359407667692572713,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Android Automation",
        "keyword": "Android Device Automation",
        "query": "title:(android device automation)",
        "channel_id": 1359407667692572713,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },

    # ─── STEALTH AUTOMATION ──────────────────────────────────────────────────
    # Channel: #stealth-mode
    # contractor_tier: ["3"]  Expert ONLY
    {
        "category": "Stealth Automation",
        "keyword": "Multilogin",
        "query": "title:(Multilogin) OR description:(Multilogin)",
        "channel_id": 1359040879121403965,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["3"],
        }
    },
    {
        "category": "Stealth Automation",
        "keyword": "GoLogin",
        "query": "title:(GoLogin) OR description:(GoLogin)",
        "channel_id": 1359040879121403965,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["3"],
        }
    },
    {
        "category": "Stealth Automation",
        "keyword": "Incognition",
        "query": "title:(Incognition) OR description:(Incognition)",
        "channel_id": 1359040879121403965,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["3"],
        }
    },
    {
        "category": "Stealth Automation",
        "keyword": "AdsPower",
        "query": "title:(AdsPower) OR description:(AdsPower)",
        "channel_id": 1359040879121403965,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["3"],
        }
    },
    {
        "category": "Stealth Automation",
        "keyword": "Browser Fingerprint",
        "query": 'title:("browser fingerprint") OR description:("browser fingerprint")',
        "channel_id": 1359040879121403965,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["3"],
        }
    },
    {
        "category": "Stealth Automation",
        "keyword": "Antidetect Browser",
        "query": "title:(antidetect) OR description:(antidetect browser)",
        "channel_id": 1359040879121403965,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["3"],
        }
    },
    {
        "category": "Stealth Automation",
        "keyword": "Social Media Automation",
        "query": 'title:("social media automation")',
        "channel_id": 1359040879121403965,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["3"],
        }
    },

    # ─── AI AUTOMATION ───────────────────────────────────────────────────────
    # Channel: #ai-automation
    # contractor_tier: ["1","2","3"]  ALL levels
    {
        "category": "AI Automation",
        "keyword": "n8n",
        "query": "n8n",
        "channel_id": 1372474025476882532,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["1", "2", "3"],
        }
    },
    {
        "category": "AI Automation",
        "keyword": "Make.com",
        "query": "make.com",
        "channel_id": 1372474025476882532,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["1", "2", "3"],
        }
    },
    {
        "category": "AI Automation",
        "keyword": "Zapier",
        "query": "zapier",
        "channel_id": 1372474025476882532,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["1", "2", "3"],
        }
    },
    {
        "category": "AI Automation",
        "keyword": "Pipedream",
        "query": "pipedream",
        "channel_id": 1372474025476882532,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["1", "2", "3"],
        }
    },

    # ─── WEB DEVELOPMENT ─────────────────────────────────────────────────────
    # Channel: #web-dev
    # contractor_tier: ["2","3"]  Intermediate + Expert
    {
        "category": "Web Development",
        "keyword": "React / Next.js Developer",
        "query": "title:(React developer) OR title:(Next.js developer) OR title:(NextJS developer)",
        "channel_id": 1364551909251223594,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Web Development",
        "keyword": "Python Web Developer",
        "query": "title:(Django developer) OR title:(Flask developer) OR title:(Python web developer)",
        "channel_id": 1364551909251223594,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Web Development",
        "keyword": "Full Stack Developer",
        "query": "title:(full stack developer) OR title:(MERN developer) OR title:(fullstack developer)",
        "channel_id": 1364551909251223594,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },

    # ─── TIKTOK SHOP ─────────────────────────────────────────────────────────
    # Channel: #tiktok-shop
    # contractor_tier: ["1","2","3"]  ALL levels
    {
        "category": "TikTok Shop",
        "keyword": "TikTok Shop Manager",
        "query": "(TikTok AND Shop AND Manager)",
        "channel_id": 1371453441938817054,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["1", "2", "3"],
        }
    },

    # ─── GENERAL AUTOMATION ──────────────────────────────────────────────────
    # Channel: #automation
    # contractor_tier: ["2","3"]  Intermediate + Expert
    {
        "category": "Automation",
        "keyword": "Bot Development",
        "query": "title:(bot development) OR title:(automation bot) OR title:(discord bot) OR title:(instagram bot) OR title:(telegram bot) OR title:(twitter bot) OR title:(youtube bot)",
        "channel_id": 1359040738507358340,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Automation",
        "keyword": "Browser Automation Tools",
        "query": "title:(selenium automation) OR title:(puppeteer) OR title:(playwright automation) OR title:(web scraping bot) OR title:(browser automation)",
        "channel_id": 1359040738507358340,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Automation",
        "keyword": "Browser Automation",
        "query": "browser automation",
        "channel_id": 1359040738507358340,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
    {
        "category": "Automation",
        "keyword": "Android Accessibility Service",
        "query": "Android Accessibility Service",
        "channel_id": 1359040738507358340,
        "filters": {
            "payment_verified": True,
            "contractor_tier": ["2", "3"],
        }
    },
]
