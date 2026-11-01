from services.medicine_matcher import MedicineMatcher
m = MedicineMatcher()
print(m.find_matches('Augmentin'))
m.close()
