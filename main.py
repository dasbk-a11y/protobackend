"""
Protozap Backend — FastAPI
On-demand precision metal fabrication platform.
Run: uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import uuid, hashlib, random, uvicorn

app = FastAPI(title="Protozap API", version="1.0.0", docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer(auto_error=False)

_users: Dict = {}
_orders: Dict = {}
_quotes: Dict = {}


# ─── Schemas ─────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    name: str; email: EmailStr; password: str; company: Optional[str] = None
class UserLogin(BaseModel):
    email: EmailStr; password: str
class QuoteItem(BaseModel):
    file_name: str; material_id: str; thickness: float; quantity: int
    services: List[str] = []; width: Optional[float] = None; height: Optional[float] = None
class QuoteRequest(BaseModel):
    items: List[QuoteItem]; lead_time: str = "standard_2_day"; notes: Optional[str] = None
class OrderCreate(BaseModel):
    quote_id: str; shipping_address: Dict[str, str]
    payment_method: str = "card"; po_number: Optional[str] = None
class ContactMsg(BaseModel):
    name: str; email: EmailStr; phone: Optional[str] = None
    company: Optional[str] = None; subject: str; message: str
class AffiliateApp(BaseModel):
    name: str; email: EmailStr; website: Optional[str] = None
    audience_size: Optional[str] = None; platform: Optional[str] = None; description: str
class SponsorApp(BaseModel):
    school_name: str; contact_name: str; email: EmailStr
    phone: Optional[str] = None; program_description: str
class SpotlightApp(BaseModel):
    org_name: str; contact_name: str; email: EmailStr
    phone: Optional[str] = None; description: str

# ─── Static Data ─────────────────────────────────────────────────────────────
MATERIALS = [
  {"id":"steel-a36","name":"Steel A36 HR Mill Finish","category":"steel","description":"Standard hot-rolled structural steel. Most popular for general fabrication.","grades":["A36","A1011"],"base_price":3.80,"supports_bending":True,"supports_tapping":True,"supports_powder_coating":True,"color_hex":"#6B6B6B","thicknesses":[{"value":1.5,"label":"1.5mm"},{"value":1.9,"label":"1.9mm"},{"value":2.5,"label":"2.5mm"},{"value":4.8,"label":"4.8mm"},{"value":6.4,"label":"6.4mm"},{"value":9.5,"label":"9.5mm"},{"value":12.5,"label":"12.5mm"},{"value":19.0,"label":"19mm"},{"value":25.0,"label":"25mm"}],"max_size":"3020mm × 1500mm"},
  {"id":"steel-cr","name":"Steel A1008 Cold-Rolled","category":"steel","description":"Cold-rolled steel with a smooth, consistent surface ideal for precision parts.","grades":["A1008 CR"],"base_price":4.40,"supports_bending":True,"supports_tapping":True,"supports_powder_coating":True,"color_hex":"#808080","thicknesses":[{"value":0.6,"label":"0.6mm"},{"value":0.9,"label":"0.9mm"},{"value":1.2,"label":"1.2mm"},{"value":1.5,"label":"1.5mm"},{"value":1.9,"label":"1.9mm"}],"max_size":"3020mm × 1500mm"},
  {"id":"steel-ar500","name":"Steel AR500 Abrasion Resistant","category":"steel","description":"Hardened abrasion-resistant steel for targets, wear plates, and armor.","grades":["AR500"],"base_price":10.00,"supports_bending":False,"supports_tapping":True,"supports_powder_coating":False,"color_hex":"#5A5A5A","thicknesses":[{"value":4.8,"label":"4.8mm"},{"value":6.4,"label":"6.4mm"},{"value":9.5,"label":"9.5mm"},{"value":12.5,"label":"12.5mm"}],"max_size":"2413mm × 1194mm"},
  {"id":"ss-304-2b","name":"Stainless Steel 304 #2B","category":"stainless","description":"Most common stainless grade. Excellent corrosion resistance and smooth finish.","grades":["304 #2B"],"base_price":15.00,"supports_bending":True,"supports_tapping":True,"supports_powder_coating":False,"color_hex":"#C0C0C0","thicknesses":[{"value":0.9,"label":"0.9mm"},{"value":1.2,"label":"1.2mm"},{"value":1.5,"label":"1.5mm"},{"value":1.9,"label":"1.9mm"},{"value":2.5,"label":"2.5mm"},{"value":6.4,"label":"6.4mm"},{"value":12.5,"label":"12.5mm"}],"max_size":"3020mm × 1500mm"},
  {"id":"ss-304-brushed","name":"Stainless Steel 304 #4 Brushed","category":"stainless","description":"Brushed stainless with a directional grain. Premium aesthetic for visible parts.","grades":["304 #4 Brushed"],"base_price":18.50,"supports_bending":True,"supports_tapping":True,"supports_powder_coating":False,"color_hex":"#B8B8B8","thicknesses":[{"value":1.2,"label":"1.2mm"},{"value":1.5,"label":"1.5mm"},{"value":1.9,"label":"1.9mm"}],"max_size":"3020mm × 1500mm"},
  {"id":"ss-316","name":"Stainless Steel 316 #2B","category":"stainless","description":"Marine-grade stainless with superior corrosion resistance for harsh environments.","grades":["316 #2B"],"base_price":24.00,"supports_bending":True,"supports_tapping":True,"supports_powder_coating":False,"color_hex":"#A8A8A8","thicknesses":[{"value":1.2,"label":"1.2mm"},{"value":1.9,"label":"1.9mm"},{"value":6.4,"label":"6.4mm"},{"value":12.5,"label":"12.5mm"}],"max_size":"3020mm × 1500mm"},
  {"id":"al-5052","name":"Aluminum 5052 H32","category":"aluminum","description":"Most popular aluminum grade. Formable, corrosion resistant, affordable.","grades":["5052 H32"],"base_price":8.00,"supports_bending":True,"supports_tapping":True,"supports_powder_coating":True,"color_hex":"#D4D4C0","thicknesses":[{"value":0.5,"label":"0.5mm"},{"value":1.0,"label":"1mm"},{"value":1.6,"label":"1.6mm"},{"value":3.2,"label":"3.2mm"},{"value":6.4,"label":"6.4mm"},{"value":12.5,"label":"12.5mm"}],"max_size":"3020mm × 1500mm"},
  {"id":"al-6061","name":"Aluminum 6061 T6","category":"aluminum","description":"High-strength aluminum alloy excellent for structural and machined applications.","grades":["6061 T6"],"base_price":9.25,"supports_bending":True,"supports_tapping":True,"supports_powder_coating":True,"color_hex":"#C8C8B4","thicknesses":[{"value":1.6,"label":"1.6mm"},{"value":3.2,"label":"3.2mm"},{"value":6.4,"label":"6.4mm"},{"value":12.5,"label":"12.5mm"},{"value":19.0,"label":"19mm"},{"value":25.0,"label":"25mm"}],"max_size":"3020mm × 1194mm"},
  {"id":"copper-110","name":"Copper 110 Annealed","category":"copper","description":"Soft, highly conductive ETP copper. Ideal for electrical and thermal applications.","grades":["110 Annealed"],"base_price":29.50,"supports_bending":True,"supports_tapping":True,"supports_powder_coating":False,"color_hex":"#B87333","thicknesses":[{"value":0.8,"label":"0.8mm"},{"value":1.6,"label":"1.6mm"},{"value":3.2,"label":"3.2mm"}],"max_size":"584mm × 584mm"},
  {"id":"brass-260","name":"Brass 260 Cartridge","category":"brass_bronze","description":"Ultra-formable 'cartridge' brass. Excellent for decorative and precision parts.","grades":["260 Brass"],"base_price":35.00,"supports_bending":True,"supports_tapping":True,"supports_powder_coating":False,"color_hex":"#D4AF37","thicknesses":[{"value":0.8,"label":"0.8mm"},{"value":1.6,"label":"1.6mm"},{"value":3.2,"label":"3.2mm"},{"value":6.4,"label":"6.4mm"}],"max_size":"584mm × 584mm"},
]

SERVICES = [
  {"id":"laser-cutting","name":"Sheet Laser Cutting","slug":"laser-cutting","short_desc":"8–10 kW fiber lasers, ±0.005\", up to 1\" thick.","description":"High-powered 8–10 kW fiber lasers cut your parts with ±0.005\" precision. From 0.005\" shim stock to 1\" plate. Zero taper, minimal burr, exceptional edge quality.","capabilities":["8 kW and 10 kW fiber lasers","Thickness: 0.005\" to 1.0\"","Part size: up to 119\" × 59\"","Accuracy: ±0.005\"","All 6 metal families","Near-zero burr on aluminum to 1\""],"lead_time_days":2,"featured":True},
  {"id":"tube-cutting","name":"Laser Tube Cutting","slug":"tube-cutting","short_desc":"6 kW tube lasers up to 10\" OD with instant DFM.","description":"6 kW tube lasers cut circular, square, and rectangular profiles up to 10\" OD. Bevel cuts to 45°. The only platform with instant in-browser DFM for tube parts.","capabilities":["6 kW dedicated tube lasers","Up to 10\" OD round profiles","Wall thickness up to 3/8\"","Bevel cuts to 45°","250+ tube profiles in stock","In-browser DFM checks"],"lead_time_days":2,"featured":True},
  {"id":"bending","name":"Brake Bending","slug":"bending","short_desc":"CNC bending with live 3D simulation and collision detection.","description":"CNC press brake bending with ±0.0001\" back-gauge precision. Upload a 3D model or flat pattern. Auto-unfolding, real-time bend simulation, and collision detection — all online.","capabilities":["Max: 3/4\" steel, 1/2\" stainless","Max bend length: 119\"","Back-gauge: ±0.0001\"","Angle tolerance: ±1.0°","Auto-unfolds STEP/SLDPRT","Tooling collision detection"],"lead_time_days":2,"featured":True},
  {"id":"cnc-tube-bending","name":"CNC Tube Bending","slug":"cnc-tube-bending","short_desc":"World's only in-browser DFM for bent tube.","description":"Mandrel CNC bending for round tubes up to 1.5\" OD. World's only in-browser DFM for bent tube. Combine with tube laser cutting for complete assemblies.","capabilities":["Round tube: 0.75\" to 1.5\" OD","Steel A513, DOM, 4130, SS, Aluminum","World-first in-browser DFM","Fish-mouth end prep","Multi-bend complex geometry"],"lead_time_days":3,"featured":False},
  {"id":"hardware-insertion","name":"Hardware Insertion","slug":"hardware-insertion","short_desc":"400+ PEM fasteners with instant DFM verification.","description":"Press-fit installation of 400+ PEM self-clinching fasteners. DFM software auto-verifies material thickness, clearances, and bend angles.","capabilities":["400+ PEM brand fasteners","Threaded studs, nuts, standoffs","Auto DFM verification","Compatible with bent parts","Replaces welding in many cases"],"lead_time_days":3,"featured":False},
  {"id":"tapping","name":"Metal Tapping","slug":"tapping","short_desc":"#6-32 to 1.5\" and M3–M36, auto-detected from 3D.","description":"CNC thread tapping in standard 6-32 to 1-1/2\"-6 and metric M3×0.5 to M36×4.0. From under $10 for the first hole. Auto-detected from your 3D model.","capabilities":["Standard: #6-32 to 1-1/2\"-6","Metric: M3×0.5 to M36×4.0","< $10 first hole","All metals","Auto-detected from 3D"],"lead_time_days":2,"featured":False},
  {"id":"countersinking","name":"Countersinking","slug":"countersinking","short_desc":"82° and 90° countersinks, auto-detected.","description":"82° (Imperial) and 90° (Metric) conical holes for flush hardware seating. Auto-detected from 3D. Works on steel and stainless — unlike competitors who only offer aluminum.","capabilities":["82° Imperial / 90° Metric","Min material: 18 gauge","Works on steel + stainless","Auto-detected from 3D","Matches popular hardware vendors"],"lead_time_days":2,"featured":False},
  {"id":"deburring","name":"Deburring & Grain Finish","slug":"deburring","short_desc":"Remove burrs + optional 240-grit linear grain finish.","description":"Remove burrs and optionally apply a 240-grit linear grain finish. Available on aluminum and stainless. Preps parts for welding, painting, or powder coating.","capabilities":["Removes laser cutting burrs","Optional 240-grit linear grain","Available on Al and SS","Auto-applied at checkout"],"lead_time_days":1,"featured":False},
  {"id":"bead-blasting","name":"Bead Blasting","slug":"bead-blasting","short_desc":"100 psi glass beads for uniform matte finish.","description":"100 psi recycled glass bead blasting creates a uniform matte finish. Eco-friendly, no chemicals. Removes burn marks, slag, rust. Preps for coating or plating.","capabilities":["Recycled glass beads at 100 psi","Uniform matte finish","No chemicals — eco-friendly","Removes burn marks and rust","Coating-ready surface"],"lead_time_days":3,"featured":False},
  {"id":"tumbling","name":"Centrifugal Tumbling","slug":"tumbling","short_desc":"225 RPM batch polishing for small-medium parts.","description":"Up to 225 RPM batch polishing for small-to-medium parts. Parts up to 8\"×4\"×4\". 1.4 cu ft per run. Aerospace, medical, and mass production applications.","capabilities":["Up to 225 RPM","Max part: 8\" × 4\" × 4\"","1.4 cu ft per run","Aerospace and medical grade","Pre-powder coat preparation"],"lead_time_days":3,"featured":False},
  {"id":"powder-coating","name":"Powder Coating","slug":"powder-coating","short_desc":"17 Prismatic Powder colors, instant pricing, weatherproof.","description":"17 standard Prismatic Powder colors. Parts up to 60\" and 50 lbs. Scratch and chip-resistant weatherproof finish. Instant pricing — no waiting.","capabilities":["17 Prismatic Powder colors","Max weight: 50 lbs","Max size: 60\"","Scratch and chip-resistant","Weatherproof finish","Instant online pricing"],"lead_time_days":6,"featured":True},
]

TUTORIALS = [
  {"id":"t1","title":"Getting Started with Instant Quoting","description":"Complete walkthrough: upload, select materials, and place your first order.","duration_minutes":8,"category":"Getting Started","tags":["beginner","quoting"]},
  {"id":"t2","title":"Working Through Design Warnings","description":"Understand DFM warnings and use the in-browser editor to fix issues before ordering.","duration_minutes":11,"category":"DFM","tags":["dfm","warnings"]},
  {"id":"t3","title":"Designing Bent Parts in Fusion 360","description":"Prepare 3D sheet metal models for automatic unfolding and instant bend simulation.","duration_minutes":15,"category":"Bending","tags":["bending","fusion360"]},
  {"id":"t4","title":"CNC Tube Bending: LRA vs XYZ","description":"Compare Length-Rotation-Angle vs XYZ coordinate inputs for tube bend design.","duration_minutes":12,"category":"Tube Bending","tags":["tube","coordinates"]},
  {"id":"t5","title":"Advanced Nesting and Volume Pricing","description":"Learn how our nesting engine works and how to maximize volume discounts.","duration_minutes":9,"category":"Pricing","tags":["nesting","pricing"]},
  {"id":"t6","title":"Hardware Insertion with PEM Fasteners","description":"Configure PEM fastener placement, auto-resize holes, and run DFM checks.","duration_minutes":10,"category":"Hardware","tags":["hardware","pem"]},
  {"id":"t7","title":"Multi-Part Configuration","description":"Configure multiple parts simultaneously to get the best nested pricing.","duration_minutes":7,"category":"Getting Started","tags":["multi-part"]},
  {"id":"t8","title":"Sending Quotes to a Colleague","description":"Use the 'Send As Quote' feature for corporate purchasing approval flows.","duration_minutes":5,"category":"Enterprise","tags":["enterprise","purchasing"]},
]

FAQ_DATA = [
  {"q":"What does 'fully-nested pricing' mean?","a":"We nest all parts in your order to minimize material usage and automatically reduce your price. Other services quote parts individually — we quote the whole job.","category":"Pricing"},
  {"q":"What are your lead times?","a":"Standard is 2 business days. Same-day and next-day options available at checkout. We always cut early when we can.","category":"Lead Times"},
  {"q":"What file formats do you accept?","a":"2D: DXF, SVG, AI. 3D: STEP, SLDPRT, CATPART, IPT, IGS, PAR, IGES, NX, SolidEdge, JT, 3DM, x_t, SAT, SAB.","category":"Files"},
  {"q":"Do you offer bending?","a":"Yes. Upload a 3D sheet metal model (auto-unfolded) or 2D flat pattern. We bend up to 3/4\" steel with instant simulation and collision detection.","category":"Services"},
  {"q":"Is there a minimum order?","a":"No minimums — ever. Order one prototype or thousands of production parts.","category":"Pricing"},
  {"q":"What's your thickness range?","a":"0.005\" shim stock up to 1.0\" plate for steel, stainless, and aluminum. Copper and brass up to 1/4\" thick.","category":"Materials"},
  {"q":"Can you ship internationally?","a":"We ship throughout the US and Canada. International shipping is planned for the future.","category":"Shipping"},
  {"q":"Do you offer net terms?","a":"Yes. We offer N30 net terms to active customers. Email support@protozap.com to apply.","category":"Enterprise"},
]

# ─── Helpers ─────────────────────────────────────────────────────────────────
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()
def get_user(c: HTTPAuthorizationCredentials = Depends(security)):
    if not c: raise HTTPException(401, "Not authenticated")
    for u in _users.values():
        if u.get("token") == c.credentials: return u
    raise HTTPException(401, "Invalid token")

def calc_price(mat_id, w, h, qty, svcs):
    m = next((x for x in MATERIALS if x["id"] == mat_id), None)
    rate = m["base_price"] if m else 0.05
    base = rate * (w or 4.0) * (h or 4.0) * qty
    extras = {"bending":1250,"tapping":675,"countersinking":420,"powder_coating":2100,
               "bead_blasting":1000,"tumbling":840,"hardware_insertion":1500}
    for s in svcs: base += extras.get(s, 0) * qty
    return round(base, 2)

# ─── Auth ─────────────────────────────────────────────────────────────────────
auth_r = APIRouter(prefix="/api/auth", tags=["Auth"])

@auth_r.post("/register")
def register(b: UserRegister):
    if any(u["email"] == b.email for u in _users.values()):
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4()); token = str(uuid.uuid4())
    user = {"id":uid,"name":b.name,"email":b.email,"company":b.company,"token":token,
            "pw":hash_pw(b.password),"created_at":datetime.utcnow().isoformat()}
    _users[uid] = user
    return {"access_token":token,"token_type":"bearer",
            "user":{k:v for k,v in user.items() if k not in ("pw","token")}}

@auth_r.post("/login")
def login(b: UserLogin):
    u = next((x for x in _users.values() if x["email"] == b.email), None)
    if not u or u["pw"] != hash_pw(b.password): raise HTTPException(401, "Invalid credentials")
    u["token"] = str(uuid.uuid4())
    return {"access_token":u["token"],"token_type":"bearer",
            "user":{k:v for k,v in u.items() if k not in ("pw","token")}}

@auth_r.get("/me")
def me(u=Depends(get_user)):
    return {k:v for k,v in u.items() if k not in ("pw","token")}

# ─── Materials ────────────────────────────────────────────────────────────────
mat_r = APIRouter(prefix="/api/materials", tags=["Materials"])

@mat_r.get("/")
def list_mats(category: Optional[str] = None):
    m = [x for x in MATERIALS if not category or x["category"] == category]
    return {"materials": m, "total": len(m)}

@mat_r.get("/categories")
def mat_cats():
    return {"categories": list({m["category"] for m in MATERIALS})}

@mat_r.get("/{mid}")
def get_mat(mid: str):
    m = next((x for x in MATERIALS if x["id"] == mid), None)
    if not m: raise HTTPException(404, "Not found")
    return m

# ─── Services ─────────────────────────────────────────────────────────────────
svc_r = APIRouter(prefix="/api/services", tags=["Services"])

@svc_r.get("/")
def list_svcs(featured_only: bool = False):
    s = [x for x in SERVICES if not featured_only or x.get("featured")]
    return {"services": s, "total": len(s)}

@svc_r.get("/{slug}")
def get_svc(slug: str):
    s = next((x for x in SERVICES if x["slug"] == slug), None)
    if not s: raise HTTPException(404, "Not found")
    return s

# ─── Quote ────────────────────────────────────────────────────────────────────
quote_r = APIRouter(prefix="/api/quote", tags=["Quote"])

@quote_r.post("/")
def create_quote(b: QuoteRequest):
    items_out, subtotal, nesting = [], 0.0, 0.0
    for item in b.items:
        m = next((x for x in MATERIALS if x["id"] == item.material_id), None)
        price = calc_price(item.material_id, item.width or 4, item.height or 4, item.quantity, item.services)
        warns = []
        if item.quantity == 1: warns.append("Order 5+ for volume discounts")
        items_out.append({"file_name":item.file_name,"material_name":m["name"] if m else "Unknown",
                          "thickness":item.thickness,"quantity":item.quantity,"services":item.services,
                          "unit_price":round(price/item.quantity,2),"total_price":price,"dfm_warnings":warns})
        subtotal += price
    if len(b.items) > 2: nesting = round(subtotal * 0.08, 2)
    shipping = 0.0 if subtotal > 17000 else 1550.0
    total = round(subtotal - nesting + shipping, 2)
    days = {"same_day":0,"next_day":1,"standard_2_day":2,"standard_3_day":3}.get(b.lead_time, 2)
    qid = str(uuid.uuid4())[:8].upper()
    result = {"quote_id":qid,"items":items_out,"subtotal":round(subtotal,2),"shipping":shipping,
              "total":total,"lead_time":b.lead_time,
              "estimated_ship_date":(datetime.utcnow()+timedelta(days=days)).strftime("%Y-%m-%d"),
              "valid_until":(datetime.utcnow()+timedelta(days=30)).strftime("%Y-%m-%d"),"nesting_savings":nesting}
    _quotes[qid] = result; return result

@quote_r.get("/{qid}")
def get_quote(qid: str):
    q = _quotes.get(qid)
    if not q: raise HTTPException(404, "Not found")
    return q

# ─── Orders ───────────────────────────────────────────────────────────────────
order_r = APIRouter(prefix="/api/orders", tags=["Orders"])

@order_r.post("/")
def create_order(b: OrderCreate, u=Depends(get_user)):
    q = _quotes.get(b.quote_id)
    if not q: raise HTTPException(404, "Quote not found")
    oid = f"PZ-{str(uuid.uuid4())[:6].upper()}"
    order = {"id":oid,"user_id":u["id"],"status":"confirmed",
             "created_at":datetime.utcnow().isoformat(),"estimated_ship":q["estimated_ship_date"],
             "items":[{"part_name":i["file_name"],"material":i["material_name"],
                       "quantity":i["quantity"],"status":"queued","completion_pct":0} for i in q["items"]],
             "total":q["total"],"shipping_address":b.shipping_address,
             "tracking_number":None,"po_number":b.po_number}
    _orders[oid] = order
    return {"order_id":oid,"status":"confirmed","message":"Order placed successfully"}

@order_r.get("/")
def list_orders(u=Depends(get_user)):
    return {"orders":[o for o in _orders.values() if o["user_id"]==u["id"]]}

@order_r.get("/{oid}")
def get_order(oid: str, u=Depends(get_user)):
    o = _orders.get(oid)
    if not o or o["user_id"] != u["id"]: raise HTTPException(404, "Not found")
    return o

# ─── Contact & Partners ───────────────────────────────────────────────────────
contact_r = APIRouter(prefix="/api/contact", tags=["Contact"])

@contact_r.post("/")
def contact(b: ContactMsg):
    return {"success":True,"message":"Message received. We'll respond within 1 business day."}

@contact_r.post("/affiliate")
def affiliate(b: AffiliateApp):
    return {"success":True,"message":"Application received. We'll be in touch within 3 days."}

@contact_r.post("/sponsorship")
def sponsorship(b: SponsorApp):
    return {"success":True,"message":"Sponsorship received. Approval within 1–3 business days."}

@contact_r.post("/spotlight")
def spotlight(b: SpotlightApp):
    return {"success":True,"message":"Spotlight application received. Our team will reach out soon."}

# ─── Tutorials ────────────────────────────────────────────────────────────────
tut_r = APIRouter(prefix="/api/tutorials", tags=["Tutorials"])

@tut_r.get("/")
def list_tuts(category: Optional[str] = None):
    t = [x for x in TUTORIALS if not category or x["category"] == category]
    return {"tutorials": t, "total": len(t)}

@tut_r.get("/categories")
def tut_cats():
    return {"categories": list({t["category"] for t in TUTORIALS})}

# ─── Resources ────────────────────────────────────────────────────────────────
res_r = APIRouter(prefix="/api/resources", tags=["Resources"])

@res_r.get("/faq")
def get_faq(category: Optional[str] = None):
    items = [f for f in FAQ_DATA if not category or f["category"] == category]
    return {"faq": items, "total": len(items)}

@res_r.get("/enterprise")
def enterprise():
    return {"purchasing":[{"name":"Net Terms (N30)","desc":"B2B invoicing for active customers"},{"name":"Send As Quote","desc":"Engineers configure → send payment link to purchasing"},{"name":"Company Accounts","desc":"Multiple users share files, orders, billing"},{"name":"Blanket POs","desc":"Lock in volume pricing, receive in staggered batches"}],"order_management":[{"name":"Part Libraries","desc":"Unique part numbers for exact repeat orders"},{"name":"Live Production Tracking","desc":"Per-part status with partial shipment options"},{"name":"Traceable Mill Certs","desc":"Attached to every order"},{"name":"Vendor Managed Inventory","desc":"Coming soon — bank of ready-to-ship parts"}]}

@res_r.get("/design-guide")
def design_guide():
    return {"sections":[{"title":"Getting Started","articles":[{"title":"Preparing Part Outlines","slug":"outlines"},{"title":"Understanding Micro-Joints","slug":"micro-joints"}]},{"title":"Bending","articles":[{"title":"How Bending Works","slug":"bending-basics"},{"title":"Bending Design Rules","slug":"bending-rules"}]},{"title":"Tube Cutting","articles":[{"title":"Tube Cutting Basics","slug":"tube-basics"}]},{"title":"Powder Coating","articles":[{"title":"Selecting Colors","slug":"powder-colors"}]}]}

# ─── Upload ───────────────────────────────────────────────────────────────────
upload_r = APIRouter(prefix="/api/upload", tags=["Upload"])

@upload_r.post("/")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    ext = file.filename.split(".")[-1].lower()
    fid = str(uuid.uuid4())[:8]
    s2d = {"dxf","svg","ai"}; s3d = {"step","stp","sldprt","catpart","ipt","igs","iges","par","jt","3dm","x_t","sat","sab"}
    if ext in s2d: warns,errs,st = ["Ensure all contours are closed"],[],  "ok"
    elif ext in s3d: warns,errs,st = [],[],  "ok"
    else: warns,errs,st = [],[f"Unsupported format .{ext}"],"error"
    return {"file_id":fid,"filename":file.filename,"file_size":len(content),"file_type":ext,"dfm_status":st,
            "warnings":warns,"errors":errs,"dimensions":{"width":round(random.uniform(2,24),2),"height":round(random.uniform(2,18),2)} if not errs else None}

@upload_r.get("/dfm/{fid}")
def dfm_result(fid: str):
    return {"file_id":fid,"status":"ok","checks":[{"name":"Contour closure","status":"pass","message":"All contours closed"},{"name":"Minimum feature size","status":"pass","message":"Smallest feature 0.12\" — within limits"},{"name":"Duplicate geometry","status":"pass","message":"No overlapping geometry"},{"name":"Hole diameter","status":"warning","message":"2 holes near minimum size for selected material"}],"estimated_cut_time":round(random.uniform(0.5,4.5),1),"perimeter":round(random.uniform(8,80),2),"area":round(random.uniform(4,200),2)}

for r in [auth_r, mat_r, svc_r, quote_r, order_r, contact_r, tut_r, res_r, upload_r]:
    app.include_router(r)

@app.get("/")
def root(): return {"message":"Protozap API","version":"1.0.0","docs":"/api/docs"}

@app.get("/api/health")
def health(): return {"status":"healthy","timestamp":datetime.utcnow().isoformat()}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
