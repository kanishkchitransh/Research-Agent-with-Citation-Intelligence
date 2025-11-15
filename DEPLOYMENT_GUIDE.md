# Hugging Face Spaces Deployment Guide

## 🚀 Deploy Your Research Agent to Hugging Face Spaces (FREE!)

### Prerequisites
- GitHub account
- Hugging Face account (free): https://huggingface.co/join
- Your Google AI API key
- Your Perplexity API key (optional)

---

## Step 1: Create Hugging Face Space

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Fill in details:
   - **Space name**: `research-agent-citation-intelligence` (or your choice)
   - **License**: MIT
   - **SDK**: Gradio
   - **SDK version**: 4.16.0 (or latest)
   - **Space hardware**: CPU basic (FREE)
   - **Visibility**: Public (or Private if you prefer)

4. Click **"Create Space"**

---

## Step 2: Upload Code to HF Spaces

### Option A: Using Git (Recommended)

```bash
# Navigate to your project
cd C:\Users\hp\Research-Agent-with-Citation-Intelligence

# Add HF Spaces as remote (replace USERNAME and SPACE_NAME)
git remote add hf https://huggingface.co/spaces/USERNAME/SPACE_NAME

# Push to HF Spaces
git push hf main
```

### Option B: Using Web Interface

1. In your HF Space, click **"Files"** tab
2. Upload these files/folders:
   ```
   app.py                 # Entry point (REQUIRED)
   requirements.txt       # Dependencies
   agent/                 # All files in agent folder
   rag/                   # All files in rag folder
   citation/              # All files in citation folder
   ui/                    # All files in ui folder
   config.py              # Configuration
   .env.example          # Example env file
   ```

3. Upload the README:
   - Rename `HF_SPACES_README.md` to `README.md`
   - Upload it (this becomes the Space's front page)

---

## Step 3: Configure Secrets (API Keys)

**IMPORTANT**: Never commit API keys to git!

1. Go to your Space's **Settings** tab
2. Scroll to **"Repository secrets"**
3. Add these secrets:

   **Secret 1:**
   - Name: `HF_GOOGLE_API_KEY`
   - Value: Your Google AI API key (get from https://makersuite.google.com/app/apikey)

   **Secret 2:**
   - Name: `HF_PERPLEXITY_API_KEY`
   - Value: Your Perplexity API key (get from https://www.perplexity.ai/api-platform)

4. Click **"Add secret"** for each

These will be automatically loaded in `app.py`.

---

## Step 4: Wait for Build

1. HF Spaces will automatically:
   - Install dependencies from `requirements.txt`
   - Build the app
   - Launch it

2. Watch the **"Logs"** tab for progress

3. Build time: ~5-10 minutes (first time)

4. When ready, you'll see: ✅ **"Running"**

---

## Step 5: Test Your Deployed App

1. Click your Space URL: `https://huggingface.co/spaces/USERNAME/SPACE_NAME`

2. Test it:
   - Upload a research paper (PDF)
   - Extract citations
   - Explain a citation
   - Verify Perplexity search works

3. If it works: 🎉 **SUCCESS!**

---

## Step 6: Share Your App

### Get Shareable Links:

1. **Direct link**: `https://huggingface.co/spaces/USERNAME/SPACE_NAME`

2. **Embed in website**:
   ```html
   <iframe
     src="https://USERNAME-SPACE_NAME.hf.space"
     frameborder="0"
     width="850"
     height="450"
   ></iframe>
   ```

3. **Share on social media**:
   - Twitter/X: Share your Space link
   - LinkedIn: Add to your portfolio
   - GitHub: Add link to README

### Add to Portfolio:

```markdown
## Research Agent with Citation Intelligence
🔗 **Live Demo**: https://huggingface.co/spaces/USERNAME/SPACE_NAME

An AI agent that automatically finds and explains citations in research papers.
Built with Gemini AI + Perplexity Search + ReAct reasoning.
```

---

## Troubleshooting

### Issue: "Application startup failed"

**Check**:
1. Logs tab - What's the error?
2. requirements.txt - Are all dependencies listed?
3. API keys - Are secrets configured correctly?

**Common fixes**:
```bash
# If module not found errors:
- Check requirements.txt has all packages
- Ensure versions are compatible

# If API errors:
- Verify secrets are set: HF_GOOGLE_API_KEY, HF_PERPLEXITY_API_KEY
- Check secret names match exactly

# If import errors:
- Ensure all folders (agent/, rag/, citation/, ui/) are uploaded
- Check app.py exists at root level
```

### Issue: "Out of memory"

**Solution**: Upgrade to better hardware tier
1. Settings → Hardware
2. Choose CPU basic+ or GPU (may have cost)

### Issue: Citations not resolving

**Check**:
1. Is PERPLEXITY_API_KEY set in secrets?
2. Check logs for API errors
3. Try with a different paper

---

## Optimization Tips

### 1. Faster Loading

Add `.gitignore` to exclude unnecessary files:
```
__pycache__/
*.pyc
data/
logs/
test_*.py
*.md  # Except README.md
```

### 2. Custom Domain (Optional)

HF Spaces provides:
- Free subdomain: `USERNAME-SPACE_NAME.hf.space`
- Custom domain: Available in paid tiers

### 3. Analytics (Optional)

Add Google Analytics to `app.py`:
```python
# In gr.Blocks, add:
analytics_enabled=True
```

---

## Cost Breakdown

### Hugging Face Spaces:
- **FREE tier**: CPU basic (sufficient for demos)
- **Paid tiers**: $5-50/month (if you need more power)

### API Costs (Your Keys):
- **Gemini API**: FREE (with limits)
- **Perplexity API**: Check their pricing

**Total for demo**: $0/month ✅

---

## Next Steps After Deployment

1. ✅ Test with multiple papers
2. 📹 Record demo video
3. 📝 Write blog post about it
4. 🔗 Add to your resume/portfolio
5. 📧 Share with researchers in your network
6. 🌟 Collect user feedback

---

## Making Updates

### To update your deployed app:

```bash
# Make changes locally
git add .
git commit -m "Update app features"

# Push to HF Spaces
git push hf main

# HF will automatically rebuild!
```

---

## Getting Help

- **HF Spaces Docs**: https://huggingface.co/docs/hub/spaces
- **Gradio Docs**: https://gradio.app/docs
- **Community**: HF Discord, forums

---

## Success Checklist

Before going live:
- ✅ App runs locally without errors
- ✅ All files uploaded to HF Spaces
- ✅ API keys configured in secrets
- ✅ App builds successfully
- ✅ Citation explanation works end-to-end
- ✅ README looks good
- ✅ Tested with multiple papers
- ✅ Shareable link works

**When all checkboxes are ✅, you're ready to share!** 🎉

---

**Your app will be live at:**
`https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`

**Share it with the world!** 🚀
