# Minimal Vercel Deployment

This is a minimal Flask API for deploying to Vercel. It contains only the essential files needed for deployment.

## Deployment Instructions

1. Make sure you have the Vercel CLI installed:

   ```
   npm i -g vercel
   ```

2. Navigate to this directory:

   ```
   cd vercel_deploy
   ```

3. Deploy to Vercel:
   ```
   vercel
   ```

## Files

- `index.py` - The minimal Flask application
- `requirements.txt` - Minimal dependencies
- `vercel.json` - Vercel configuration
- `.gitignore` - Git ignore file

## Important Notes

- This is a minimal API deployment that avoids the 250MB size limit
- The main application functionality is not included
- Once this deploys successfully, you can gradually add features
