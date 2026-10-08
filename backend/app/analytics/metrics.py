def summarize(targets, detection_count, total_tracks):
    visible=[t for t in targets if t['status']!='LOST']
    return {"visible":len(visible),"lost":len(targets)-len(visible),
        "tracked":len(targets),"drone_count":sum(t['class_name'].startswith('drone') for t in visible),
        "average_confidence":sum(t['confidence'] for t in visible)/len(visible) if visible else None,
        "detection_count":detection_count,"total_tracks":total_tracks,
        "track_persistence":sum(t['persistence'] for t in targets)/len(targets) if targets else None,
        "id_switches":None,"precision":None,"recall":None,"map50":None,"map50_95":None}
