import streamlit as st
from collections import defaultdict
import uuid

st.set_page_config(page_title="Splittit", page_icon="💸")
st.title("💸 Splittit - bypass splitwise pro")
st.text("with this app, you can create a single entry out of multiple expenses that you paid with a descriptive report so that you can later add it in your splitwise group")

# ── Session State Initialization ─────────────────────────────────────────
if 'report_started' not in st.session_state:
    st.session_state.report_started = False
    st.session_state.people = set()     # all names seen so far
    st.session_state.entries = []       # all expense dicts
    st.session_state.num_slots = 1      # how many participant‐fields
    st.session_state.editing_id = None  # id of entry being edited

# ── Start / Reset Report ─────────────────────────────────────────────────
if not st.session_state.report_started:
    if st.button("Start a New Report"):
        st.session_state.report_started = True
        st.session_state.people.clear()
        st.session_state.entries.clear()
        st.session_state.num_slots = 1
        st.session_state.editing_id = None
    st.stop()

# ── If we’re editing, find that entry and pre-fill the form state ────────
def start_edit(entry_id):
    e = next(e for e in st.session_state.entries if e['id'] == entry_id)
    st.session_state.editing_id = entry_id
    st.session_state.amount = e['amount']
    st.session_state.expense_name = e['name']
    st.session_state.split_type = e['split']
    st.session_state.num_slots = len(e['people'])
    for i, person in enumerate(e['people']):
        st.session_state[f"slot_sel_{i}"] = person
        if e['split'] == "By Percentage":
            st.session_state[f"pct_{i}"] = e['pct'][i]
        if e['split'] == "By Shares":
            st.session_state[f"shr_{i}"] = e['shr'][i]
        if e['split'] == "Manual":
            st.session_state[f"manual_{i}"] = e['manual'][i]
    st.session_state.payer_sel = e['payer']

# ── Header ────────────────────────────────────────────────────────────────
st.header("➕ Add / Edit an Expense Entry")

# ── Expense Details ──────────────────────────────────────────────────────
amount       = st.number_input(
    "Amount",
    min_value=0.01,
    step=0.01,
    key="amount",
    value=st.session_state.get("amount", 0.01)
)
expense_name = st.text_input(
    "Expense Name",
    key="expense_name",
    value=st.session_state.get("expense_name", "")
)
split_type   = st.selectbox(
    "Split Method",
    ["Equally", "By Percentage", "By Shares", "Manual"],
    key="split_type",
    index=["Equally","By Percentage","By Shares","Manual"]
           .index(st.session_state.get("split_type","Equally"))
)

# ── Show Existing Tags ───────────────────────────────────────────────────
st.markdown("#### 🏷️ Report-Wide People")
st.write(", ".join(sorted(st.session_state.people)) or "_None yet_")

# ── Participant Inputs ──────────────────────────────────────────────────
people, percentages, shares, manuals = [], [], [], []
for i in range(st.session_state.num_slots):
    col1, col2, col3 = st.columns([3,2,1])
    opts = sorted(st.session_state.people) + ["<Add New>"] if st.session_state.people else ["<Add New>"]
    sel = col1.selectbox(f"Person {i+1}", opts, key=f"slot_sel_{i}")
    if sel == "<Add New>":
        name = col1.text_input(f"New Person {i+1}", key=f"slot_new_{i}").strip()
    else:
        name = sel
    people.append(name)

    if split_type == "By Percentage":
        pct = col2.number_input(
            f"% for {name or '…'}",
            key=f"pct_{i}",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.get(f"pct_{i}", 0.0)
        )
        percentages.append(pct)

    elif split_type == "By Shares":
        shr = col2.number_input(
            f"Shares for {name or '…'}",
            key=f"shr_{i}",
            min_value=0.0,
            value=st.session_state.get(f"shr_{i}", 0.0)
        )
        shares.append(shr)

    elif split_type == "Manual":
        m = col2.number_input(
            f"Share for {name or '…'}",
            key=f"manual_{i}",
            min_value=0.0,
            value=st.session_state.get(f"manual_{i}", 0.0)
        )
        manuals.append(m)

    # delete-this-person button
    if col3.button("🗑️", key=f"del_{i}") and st.session_state.num_slots > 1:
        # clear slot-related keys so widgets rebuild
        for key in list(st.session_state.keys()):
            if key.startswith(("slot_sel_","slot_new_","pct_","shr_","manual_")):
                del st.session_state[key]
        st.session_state.num_slots -= 1
        st.rerun()

# ── PAYER SELECTION ─────────────────────────────────────────────────────
candidates = set(st.session_state.people) | set(p for p in people if p)
opts = sorted(candidates) + ["<Add New>"] if candidates else ["<Add New>"]
sel_payer = st.selectbox("Select Payer (can be outside split)", opts, key="payer_sel")
if sel_payer == "<Add New>":
    payer = st.text_input("New Payer Name", key="payer_new",
                          value=st.session_state.get("payer_new","")).strip()
else:
    payer = sel_payer

# ── Add Person & Add / Save Entry ────────────────────────────────────────
def add_person_slot():
    st.session_state.num_slots += 1

st.button("➕ Add Person", on_click=add_person_slot)

btn_label = "➕ Add Entry" if st.session_state.editing_id is None else "💾 Save Changes"
if st.button(btn_label):
    if not expense_name:
        st.error("Give this expense a name.")
    elif not all(people):
        st.error("Every participant slot must have a name.")
    elif not payer:
        st.error("Specify who paid (or add a new payer).")
    else:
        for p in people + [payer]:
            if p:
                st.session_state.people.add(p)

        new_entry = {
            'id':     st.session_state.editing_id or str(uuid.uuid4()),
            'name':   expense_name,
            'amount': amount,
            'people': people.copy(),
            'split':  split_type,
            'pct':    percentages.copy() if split_type=="By Percentage" else None,
            'shr':    shares.copy()      if split_type=="By Shares"      else None,
            'manual': manuals.copy()    if split_type=="Manual"         else None,
            'payer':  payer
        }

        if st.session_state.editing_id is None:
            st.session_state.entries.append(new_entry)
            st.success("✅ Entry added!")
        else:
            idx = next(i for i,e in enumerate(st.session_state.entries)
                       if e['id']==st.session_state.editing_id)
            st.session_state.entries[idx] = new_entry
            st.success("💾 Changes saved!")
            st.session_state.editing_id = None

        st.session_state.num_slots = 1
        for key in list(st.session_state.keys()):
            if key.startswith(("slot_sel_","slot_new_","pct_","shr_","manual_","payer_sel","payer_new","amount","expense_name","split_type")):
                del st.session_state[key]

# ── SHOW CURRENT ENTRIES & “WHO OWES WHOM” ───────────────────────────────
if st.session_state.entries:
    st.subheader("📝 Current Entries")
    for e in st.session_state.entries:
        cols = st.columns([4,1])
        with cols[0]:
            st.markdown(f"**{e['name']}** — ₹{e['amount']} — {e['split']} — Paid by **{e['payer']}**")
        with cols[1]:
            st.button(
                "❏ Edit",
                key=f"edit_{e['id']}",
                on_click=start_edit,
                args=(e['id'],)
            )
        with st.expander("Participants & Split details"):
            for i,p in enumerate(e['people']):
                if e['split']=="Equally":
                    detail = f"owes ₹{round(e['amount']/len(e['people']),2)}"
                elif e['split']=="By Percentage":
                    detail = f"{e['pct'][i]}% → ₹{round(e['amount']*(e['pct'][i]/100),2)}"
                elif e['split']=="By Shares":
                    total_sh = sum(e['shr'])
                    detail = f"{e['shr'][i]} shares → ₹{round(e['amount']*(e['shr'][i]/total_sh),2)}"
                else:  # Manual
                    detail = f"₹{e['manual'][i]}"
                st.write(f"- **{p}** {detail}")

    balances = defaultdict(lambda: defaultdict(float))
    for e in st.session_state.entries:
        ppl, total = e['people'], e['amount']
        share = {}
        if e['split']=="Equally":
            each = total/len(ppl)
            for p in ppl: share[p]=each
        elif e['split']=="By Percentage":
            for p,pct in zip(ppl,e['pct']): share[p]=total*(pct/100)
        elif e['split']=="By Shares":
            ssum = sum(e['shr'])
            for p,s in zip(ppl,e['shr']): share[p]=total*(s/ssum)
        else:  # Manual
            for p,m in zip(ppl,e['manual']): share[p]=m

        for debtor in ppl:
            if debtor != e['payer']:
                balances[debtor][e['payer']] += round(share[debtor],2)

    st.subheader("💳 Who Owes Whom (So Far)")
    for debtor, creditors in balances.items():
        for creditor, amt in creditors.items():
            if amt>0:
                st.write(f"**{debtor}** owes **{creditor}**: ₹{amt}")
