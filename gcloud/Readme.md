# Google Cloud Funcions + Web Page
1. Create project
```console
gcloud projects create PROJECT_ID
```
2. Export credentials
```console
export GOOGLE_APPLICATION_CREDENTIALS="./covid19-jota-59ba6be5c3d7.json"
```
3. Create bucket
```console
gsutil mb gs://[BUCKET_NAME]/
```
4. Test local
```console
python main.py
```
5. Deploy function
```console
gcloud functions deploy do_calc --trigger-topic HOSPITALICED_CALC --runtime python37
```
6. Test in cloud
```console
gcloud functions call do_calc --data='{"message": "Hello World!"}'
```

7. Create google cloud scheduler that send a pub/sub topic named HOSPITALICED_CALC
8. Upload web page
```console
gsutil cp index.html  gs://covid19-jota/
gsutil cp -r css/   gs://covid19-jota/
```
