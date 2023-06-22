### How to build image
```bash
docker build -t method5-image .
```

### How to run container
```bash
docker run -d --name method5-container -p 80:80 method5-image
```