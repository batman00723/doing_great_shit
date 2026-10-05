# Permanent Media Storage Solution for Django & Render

## 1. Problem Summary: Why Images Disappear on Render
In Django, uploaded media files are saved to `MEDIA_ROOT = os.path.join(BASE_DIR, 'media')` on the server's local disk.

On cloud platforms like **Render**, the filesystem is **ephemeral (temporary)**:
- Whenever you push new code (`git push origin main`), Render triggers a **new deployment**.
- Render spins up a **brand-new container** and completely destroys the previous container's local disk.
- Any customer photos uploaded to `/media/` on the previous container are **wiped permanently**.
- The PostgreSQL database (Supabase) still retains the filename (`customer_photos/photo.jpeg`), but the physical file no longer exists on disk -> Django returns **`404 Not Found`**.
- In the frontend, `CustomerAvatar` catches the 404 error and falls back to rendering the customer's letter monogram.

---

## 2. Permanent Solutions Overview

| Solution | Setup Difficulty | Cost | Best For |
| :--- | :--- | :--- | :--- |
| **Option A: Cloudinary (Recommended)** | **Easiest (5 mins)** | Free (25 GB/month) | Zero code changes to models; automatic image optimization & fast global CDN |
| **Option B: Supabase Storage** | **Medium (15 mins)** | Free (1 GB included in your existing project) | Keeps everything inside your existing Supabase project |
| **Option C: AWS S3 / Cloudflare R2** | **Medium (20 mins)** | Free / Pennies | Enterprise grade scalability |

---

## 3. Option A: Cloudinary (Recommended — 5 Minute Setup)

Cloudinary acts as a drop-in replacement for Django's default local file storage. Once configured, every `ImageField` in Django uploads directly to Cloudinary and generates a permanent, high-speed CDN URL.

### Step 1: Install Dependencies
In your backend virtual environment:
```bash
pip install cloudinary django-cloudinary-storage
```
And add them to `requirements.txt`:
```txt
cloudinary>=1.41.0
django-cloudinary-storage>=0.3.0
```

### Step 2: Get Free Cloudinary Credentials
1. Sign up for a free account at [cloudinary.com](https://cloudinary.com).
2. On your Cloudinary Dashboard, copy:
   - **Cloud Name**
   - **API Key**
   - **API Secret**

### Step 3: Update `backend/settings.py`
Add `cloudinary_storage` and `cloudinary` to `INSTALLED_APPS` (make sure `cloudinary_storage` is above `django.contrib.staticfiles`):

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',           # <--- Add here
    'django.contrib.staticfiles',
    'cloudinary',                   # <--- Add here
    'myapi',
    'corsheaders',
    'ninja_extra',
]
```

Add Cloudinary settings at the bottom of `backend/settings.py`:
```python
# Cloudinary Storage Configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
```

### Step 4: Add Environment Variables to Render & `.env`
In your local `.env` and in **Render Dashboard -> Environment Variables**:
```env
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### Step 5: Test & Deploy
```bash
git add backend/settings.py requirements.txt
git commit -m "integrate cloudinary permanent media storage"
git push origin main
```
✅ **Done!** From now on, whenever a customer photo is uploaded, it is permanently stored on Cloudinary. Render restarts/redeploys will never delete it.

---

## 4. Option B: Supabase Storage (Using Existing Supabase Account)

Since your database is already hosted on Supabase, you can use Supabase's built-in S3-compatible storage.

### Step 1: Create a Storage Bucket in Supabase
1. Open your Supabase Dashboard: [supabase.com/dashboard](https://supabase.com/dashboard).
2. Go to **Storage** -> Click **New Bucket**.
3. Name it: `customer-photos`.
4. Toggle **Public Bucket** to **ON** (so images can be viewed without signed tokens).
5. Click **Save**.

### Step 2: Install `django-storages` & `boto3`
```bash
pip install django-storages boto3
```
Add to `requirements.txt`:
```txt
django-storages>=1.14.4
boto3>=1.35.0
```

### Step 3: Get Supabase S3 Access Keys
1. In Supabase Dashboard -> **Project Settings** -> **Storage**.
2. Under **S3 Access Keys**, generate a new Access Key:
   - Access Key ID
   - Secret Access Key
   - Endpoint URL: `https://<project-ref>.supabase.co/storage/v1/s3`
   - Region: `ap-south-1` (or your project's region)

### Step 4: Configure `backend/settings.py`
```python
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": os.getenv("SUPABASE_STORAGE_ACCESS_KEY"),
            "secret_key": os.getenv("SUPABASE_STORAGE_SECRET_KEY"),
            "bucket_name": "customer-photos",
            "endpoint_url": os.getenv("SUPABASE_STORAGE_ENDPOINT"),
            "region_name": "ap-south-1",
            "default_acl": "public-read",
            "querystring_auth": False,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
```

---

## 5. How Frontend Automatically Supports Permanent Cloud Storage

The frontend (`src/app/(app)/dashboard/customers/page.tsx`) is **already prepared** for cloud URLs:

```typescript
function getCustomerImageUrl(path?: string | null) {
  if (!path) return null;
  // If the backend returns a Cloudinary or S3 URL (starts with http/https),
  // it uses it directly without modifying it!
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  if (cleanPath.startsWith("/media/")) {
    return `https://doing-great-shit.onrender.com${cleanPath}`;
  }
  return `https://doing-great-shit.onrender.com/media${cleanPath}`;
}
```

When Cloudinary or Supabase Storage is enabled, Django stores the full permanent URL (e.g., `https://res.cloudinary.com/...` or `https://<ref>.supabase.co/storage/v1/object/public/...`), and the frontend immediately renders it across both Grid and List views with zero changes required.
