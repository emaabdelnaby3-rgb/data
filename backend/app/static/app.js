const tokenKey = "charity_token";
const getToken = () => localStorage.getItem(tokenKey);
const authHeaders = () => ({ Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" });

async function fetchOrganizations() {
  const res = await fetch('/api/organizations');
  return await res.json();
}

async function setupOrganizations() {
  const orgs = await fetchOrganizations();
  [document.getElementById('organization'), document.getElementById('directOrg')]
    .filter(Boolean)
    .forEach((select) => {
      select.innerHTML = '<option value="">اختر جمعية</option>';
      orgs.forEach((org) => {
        const option = document.createElement('option');
        option.value = org.id;
        option.textContent = org.name;
        select.appendChild(option);
      });
    });
}

document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    full_name: document.getElementById('fullName').value,
    email: document.getElementById('email').value,
    password: document.getElementById('password').value,
    role: document.getElementById('role').value,
    national_id: document.getElementById('nationalId').value || null,
    phone: document.getElementById('phone').value || null,
    organization_id: Number(document.getElementById('organization').value) || null,
  };
  const res = await fetch('/api/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await res.json();
  if (!res.ok) return alert(data.detail || 'حدث خطأ');
  localStorage.setItem(tokenKey, data.access_token);
  alert('تم التسجيل بنجاح');
});

document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    email: document.getElementById('loginEmail').value,
    password: document.getElementById('loginPassword').value,
  };
  const res = await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await res.json();
  if (!res.ok) return alert(data.detail || 'بيانات غير صحيحة');
  localStorage.setItem(tokenKey, data.access_token);
  alert('تم تسجيل الدخول');
});

document.getElementById('beneficiaryForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    monthly_income: Number(document.getElementById('monthlyIncome').value),
    family_members: Number(document.getElementById('familyMembers').value),
    medical_condition: document.getElementById('medicalCondition').value,
    documents_url: document.getElementById('documentsUrl').value,
  };
  const res = await fetch('/api/beneficiaries/register', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
  const data = await res.json();
  alert(data.message || data.detail || 'تم');
});

async function loadCases() {
  const list = document.getElementById('casesList');
  if (!list) return;
  const res = await fetch('/api/cases');
  const cases = await res.json();
  list.innerHTML = '';
  cases.forEach((item) => {
    const needed = (item.requested_amount - item.funded_amount).toFixed(2);
    const card = document.createElement('div');
    card.className = 'col-md-6';
    card.innerHTML = `
      <div class="card h-100 p-3">
        <h5>${item.title}</h5>
        <p>${item.description}</p>
        <small>الكود: ${item.case_code} | الأولوية: ${item.priority}</small>
        <strong class="d-block my-2">المطلوب المتبقي: ${needed} جنيه</strong>
        <form data-case="${item.id}" class="donationForm d-flex gap-2">
          <input type="number" class="form-control" min="1" placeholder="المبلغ" required>
          <button class="btn btn-success">تبرع</button>
        </form>
      </div>`;
    list.appendChild(card);
  });

  document.querySelectorAll('.donationForm').forEach((form) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const amount = Number(form.querySelector('input').value);
      const caseId = form.dataset.case;
      const res = await fetch(`/api/cases/${caseId}/donate`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ amount }),
      });
      const data = await res.json();
      alert(data.message ? `${data.message}\nللمحتاج: ${data.beneficiary_share}\nللجمعية: ${data.organization_share}` : (data.detail || 'فشل'));
      loadCases();
    });
  });
}

document.getElementById('directDonationForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const orgId = document.getElementById('directOrg').value;
  const amount = Number(document.getElementById('directAmount').value);
  const res = await fetch(`/api/donate/direct?organization_id=${orgId}`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ amount }),
  });
  const data = await res.json();
  alert(data.message || data.detail || 'تم');
});

async function loadAdmin() {
  if (!document.getElementById('orgChart')) return;
  const res = await fetch('/api/admin/dashboard', { headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) return;
  document.getElementById('totalDonations').textContent = `${data.total_donations} جنيه`;
  document.getElementById('donorsCount').textContent = data.donors_count;
  document.getElementById('beneficiariesCount').textContent = data.beneficiaries_count;

  new Chart(document.getElementById('orgChart'), {
    type: 'bar',
    data: {
      labels: data.donations_by_org.map((x) => x.organization),
      datasets: [{ label: 'إجمالي التبرعات', data: data.donations_by_org.map((x) => x.amount), backgroundColor: '#0d6efd' }],
    },
  });
}

setupOrganizations();
loadCases();
loadAdmin();
