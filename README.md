# chunk-compress
Chunking, dizionario, deduplica, estrazione feature.


**Clone locale:**
```sh
git clone --depth 1 --branch main https://github.com/kamaludu/chunk-compress.git chunk-compress
```

---

**Comandi Rapidi:**
```sh
chmod +x chunk.sh build_dict.sh build_dict.py compress_chunk.py verify_pipeline.sh

mkdir -p ./tmp && chmod 700 ./tmp
mkdir -p ./chunks

./chunk.sh /my/path/
./build_dict.sh
./compress_chunk.py
./verify_pipeline.sh

```

---
  
**Esempi di percorso esplicito per chunk.sh**
```sh
./chunk.sh ./path
./chunk.sh ./path/file.sh
./chunk.sh "./path/*.sh"
./chunk.sh "src/a.sh src/b.sh"
```
