# Deploying to Vercel

This document provides instructions for deploying this Flask application to Vercel.

## Prerequisites

1. A [Vercel account](https://vercel.com/signup)
2. [Vercel CLI](https://vercel.com/download) installed (optional, for command line deployment)
3. Access to your database (Supabase PostgreSQL)

## Setup for Deployment

1. Make sure all the required files are in place:

   - `vercel.json` - Configuration for Vercel
   - `wsgi.py` - WSGI entry point
   - `requirements.txt` - Dependencies

2. Set up environment variables in Vercel:
   - `DATABASE_URL` - Your PostgreSQL connection string
   - `SECRET_KEY` - A secure random string for Flask sessions
   - `VERCEL` - Set to "true"

## Deployment Steps

### Option 1: Using Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "New Project"
3. Import your GitHub repository
4. Configure the project:
   - Framework preset: Other
   - Build command: Leave empty
   - Output directory: Leave empty
   - Install command: `pip install -r requirements.txt`
5. Add Environment Variables (as listed above)
6. Click "Deploy"

### Option 2: Using Vercel CLI

1. Login to Vercel CLI:

   ```
   vercel login
   ```

2. Deploy from the project directory:

   ```
   vercel
   ```

3. Follow the prompts to configure your project.

4. Set environment variables:
   ```
   vercel env add DATABASE_URL
   vercel env add SECRET_KEY
   ```

## Post-Deployment

1. Verify that your application is running correctly:

   - Test the dashboard functionality
   - Check that database connections are working

2. Set up a custom domain (optional):
   - Go to your project settings in Vercel
   - Navigate to "Domains"
   - Add your custom domain

## Troubleshooting

- **Database connection issues**: Verify that your database connection string is correct and that your database server allows connections from Vercel's IP ranges.
- **Missing dependencies**: Make sure all required packages are listed in `requirements.txt`.
- **Static files not loading**: Check that your static files are properly referenced in your templates.
- **File upload issues**: Remember that on Vercel, file uploads are ephemeral and should be stored in `/tmp` before being processed or transferred to permanent storage.
