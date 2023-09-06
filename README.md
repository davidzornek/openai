To run the example notebook:
- `docker build -t dm .`
- `docker run -v <path to local repo>:/openai_dm/ -p 8888:8888 -it --name dm_dev dm bash`
- `jupyter notebook --allow-root --no-browser --ip=0.0.0.0 --port=8888`
- Copy-past the full jupyter url with token into your web browser and havigate to Example.ipynb.