import hashlib
from pathlib import Path
import yaml

def resolve_dataset(path):
    path=Path(path).resolve()
    data=yaml.safe_load(path.read_text())
    root=Path(data.get('path','.'))
    if not root.is_absolute(): root=(path.parent/root).resolve()
    data['path']=str(root)
    if not isinstance(data.get('names'),(dict,list)) or not data['names']:
        raise ValueError('Dataset must define non-empty names')
    names=data['names']
    if isinstance(names,dict) and set(names)!=set(range(len(names))):
        raise ValueError('Class IDs must be consecutive integers starting at zero')
    return data,root

def validate(path, splits=('train','val')):
    data,root=resolve_dataset(path);nclasses=len(data['names']);hashes={};summary={}
    for split in splits:
        folder=Path(data.get(split,''))
        if not folder.is_absolute(): folder=root/folder
        if not folder.is_dir(): raise ValueError(f'{split}: expected an image directory: {folder}')
        images=sorted(p for p in folder.rglob('*') if p.suffix.lower() in {'.jpg','.jpeg','.png','.bmp','.webp'})
        if not images: raise ValueError(f'{split}: no images found')
        objects=0;negative=0
        for image in images:
            rel=image.relative_to(root)
            parts=list(rel.parts)
            if 'images' not in parts: raise ValueError('Use images/<split> and labels/<split> structure')
            parts[parts.index('images')]='labels';label=(root/Path(*parts)).with_suffix('.txt')
            if not label.is_file(): raise ValueError(f'Missing label {label}; use empty .txt for confirmed negatives')
            lines=label.read_text().splitlines();negative+=not any(x.strip() for x in lines)
            for line in lines:
                if not line.strip(): continue
                v=list(map(float,line.split()))
                if len(v)!=5: raise ValueError(f'{label}: expected class cx cy width height')
                cls,cx,cy,w,h=v
                if not cls.is_integer() or not 0<=cls<nclasses or not all(0<=a<=1 for a in [cx,cy,w,h]) or w<=0 or h<=0:
                    raise ValueError(f'{label}: invalid normalized label')
                if cx-w/2 < -1e-5 or cy-h/2 < -1e-5 or cx+w/2 > 1.00001 or cy+h/2 > 1.00001:
                    raise ValueError(f'{label}: box exceeds image bounds')
                objects+=1
            digest=hashlib.sha256(image.read_bytes()).hexdigest()
            if digest in hashes and hashes[digest]!=split: raise ValueError(f'Exact duplicate image crosses splits: {image}')
            hashes[digest]=split
        summary[split]={'images':len(images),'objects':objects,'negative_images':negative}
    return data,summary

def resolved_yaml(path,output):
    data,_=resolve_dataset(path);output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(yaml.safe_dump(data));return str(output.resolve())
