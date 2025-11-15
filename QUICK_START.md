# Quick Start Guide - Launch Your App TODAY! 🚀

## 🎯 Goal: Get Your App Running in 30 Minutes

---

## Step 1: Test Locally (5 minutes)

### Open Terminal/Command Prompt:

```bash
# Navigate to project
cd C:\Users\hp\Research-Agent-with-Citation-Intelligence

# Run the app
python ui/gradio_app.py
```

### What You Should See:

```
🚀 Starting Research Agent Web Interface
======================================================================

⚙️  Initializing system on startup...
🔧 Initializing Research Agent...
✅ Research Agent initialized successfully!

✅ Server starting...
🌐 Access the app at: http://localhost:7860

Running on local URL:  http://127.0.0.1:7860
```

### Test It:

1. Open browser: http://localhost:7860
2. Upload a PDF from `data/papers/`
3. Extract citations
4. Explain a citation

**If it works locally → Ready to deploy!** ✅

---

## Step 2: Deploy to Hugging Face Spaces (15 minutes)

### A. Create HF Account (if needed)

1. Go to https://huggingface.co/join
2. Sign up (FREE!)
3. Verify email

### B. Create New Space

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Fill in:
   - Name: `research-agent-citation-intelligence`
   - License: MIT
   - SDK: **Gradio**
   - SDK version: 4.16.0
   - Hardware: **CPU basic** (FREE)
   - Visibility: Public

4. Click **"Create Space"**

### C. Upload Files

**Option 1: Using Git (Fast)**

```bash
cd C:\Users\hp\Research-Agent-with-Citation-Intelligence

# Add HF remote (replace YOUR_USERNAME and YOUR_SPACE_NAME)
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME

# Push to HF
git push hf claude/research-agent-setup-011CV5aUGTxmcXtTNp7MZGMz:main
```

**Option 2: Using Web Interface (Easier)**

1. In your Space, click **"Files"** → **"+ Add file"** → **"Upload files"**

2. Upload these folders/files:
   - `app.py` ← REQUIRED (entry point)
   - `requirements.txt`
   - `config.py`
   - Entire `agent/` folder
   - Entire `rag/` folder
   - Entire `citation/` folder
   - Entire `ui/` folder

3. Rename `HF_SPACES_README.md` to `README.md` and upload it

### D. Configure API Keys (IMPORTANT!)

1. Go to your Space → **Settings** tab
2. Scroll to **"Repository secrets"**
3. Add secrets:

   ```
   Name: HF_GOOGLE_API_KEY
   Value: [Your Google AI API key]
   ```

   ```
   Name: HF_PERPLEXITY_API_KEY
   Value: [Your Perplexity API key]
   ```

4. Click **"Add secret"**

**Where to get keys:**
- Google AI: https://makersuite.google.com/app/apikey
- Perplexity: https://www.perplexity.ai/api-platform

---

## Step 3: Wait for Build (5-10 minutes)

1. Go to **"Logs"** tab in your Space
2. Watch it build (installing dependencies)
3. Wait for: ✅ **"Running"**
4. Your app is LIVE!

---

## Step 4: Test & Share (5 minutes)

### Test Your Deployed App:

1. Go to: `https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`
2. Upload a paper
3. Test citation explanation
4. Verify it works!

### Share It:

**Direct Link:**
```
https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
```

**Add to Portfolio:**
```markdown
## Research Agent with Citation Intelligence
🔗 Live Demo: https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME

AI agent that finds and explains citations in research papers.
Tech: Gemini + Perplexity + ReAct + ChromaDB
```

**Share on LinkedIn:**
```
Excited to share my latest project: Research Agent with Citation Intelligence!

It helps researchers understand paper citations by automatically:
✅ Finding cited papers on the web
✅ Explaining why they're cited
✅ Using AI + multi-step reasoning

Try it live: [your HF Spaces link]

#AI #MachineLearning #Research #NLP #AgenticAI
```

---

## Troubleshooting

### Issue: App won't start locally

```bash
# Install/update Gradio
pip install --upgrade gradio

# Check Python version (need 3.10+)
python --version

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Module not found" on HF Spaces

**Fix**: Make sure all folders (agent/, rag/, citation/, ui/) are uploaded

### Issue: Citations not resolving

**Fix**: Check secrets are set correctly in HF Space settings

---

## Success Checklist ✅

Local Testing:
- ✅ App runs at http://localhost:7860
- ✅ Can upload PDF
- ✅ Citations extracted
- ✅ Citation explanation works

Deployment:
- ✅ HF Space created
- ✅ Files uploaded
- ✅ API keys configured in secrets
- ✅ Build successful
- ✅ App accessible via public URL

Sharing:
- ✅ Link added to portfolio
- ✅ Shared on LinkedIn/Twitter
- ✅ GitHub README updated with demo link

---

## What You'll Have:

1. ✅ Working local app
2. ✅ Live demo on Hugging Face Spaces (FREE!)
3. ✅ Shareable link for portfolio
4. ✅ Professional project to discuss in interviews

**Total time: 30-45 minutes** ⏱️

**Cost: $0** 💰

**Impact: Huge for your portfolio!** 🎯

---

## Next Steps (After Deployment)

1. Record demo video (5 min)
2. Write blog post about it
3. Share with researchers in your network
4. Add to resume
5. Prepare interview talking points

---

## Need Help?

- Check `DEPLOYMENT_GUIDE.md` for detailed instructions
- HF Spaces Docs: https://huggingface.co/docs/hub/spaces
- Gradio Docs: https://gradio.app/docs

**You got this!** 🚀
