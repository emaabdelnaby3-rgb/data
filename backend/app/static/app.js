const tokenKey = "charity_token";
const getToken = () => localStorage.getItem(tokenKey);
const authHeaders = () => ({ Authorization: `Bearer ${getToken()}` });

async function fetchOrganizations() {
  const res = await fetch('/api/organizations');
  return await res.json();
}

async function setupOrganizations() {
  const orgs = await fetchOrganizations();
  [document.getElementById('directOrg'), document.getElementById('filterOrg')]
    .filter(Boolean)
    .forEach((select) => {
      select.innerHTML = '<option value="">كل الجمعيات</option>';
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
    national_id: document.getElementById('nationalId').value,
    phone: document.getElementById('phone').value || null,
  };
  const res = await fetch('/api/auth/register-donor', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) return alert(data.detail || 'حدث خطأ');
  localStorage.setItem(tokenKey, data.access_token);
  alert('تم تسجيل حساب المتبرع بنجاح');
});

document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    identifier: document.getElementById('loginIdentifier').value,
    password: document.getElementById('loginPassword').value,
  };
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) return alert(data.detail || 'بيانات غير صحيحة');
  localStorage.setItem(tokenKey, data.access_token);
  alert('تم تسجيل الدخول');
});

document.getElementById('beneficiaryForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData();
  formData.append('age', document.getElementById('age').value);
  formData.append('children_count', document.getElementById('childrenCount').value);
  formData.append('monthly_income', document.getElementById('monthlyIncome').value);
  formData.append('is_married', document.getElementById('isMarried').value);
  formData.append('has_job', document.getElementById('hasJob').value);
  formData.append('salary', document.getElementById('salary').value);
  formData.append('medical_condition', document.getElementById('medicalCondition').value);
  formData.append('id_card_file', document.getElementById('idCardFile').files[0]);
  formData.append('birth_certificates_file', document.getElementById('birthsFile').files[0]);
  const extraFile = document.getElementById('extraFile').files[0];
  if (extraFile) formData.append('extra_documents_file', extraFile);

  const res = await fetch('/api/beneficiaries/register', {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  });
  const data = await res.json();
  alert(data.message || data.detail || 'تم');
});

async function loadCases() {
  const list = document.getElementById('casesList');
  if (!list) return;

  const params = new URLSearchParams();
  const org = document.getElementById('filterOrg')?.value;
  const priority = document.getElementById('filterPriority')?.value;
  if (org) params.append('organization_id', org);
  if (priority) params.append('priority', priority);

  const res = await fetch(`/api/cases?${params.toString()}`);
  const cases = await res.json();
  list.innerHTML = '';

  cases.forEach((item) => {
    const card = document.createElement('div');
    card.className = 'col-md-6';
    card.innerHTML = `
      <div class="card h-100 p-3">
        <h5>${item.title}</h5>
        <p>${item.description}</p>
        <small>الكود: ${item.case_code} | الأولوية: ${item.priority} | نسبة التغطية: ${item.progress_percent}%</small>
        <strong class="d-block my-2">المتبقي: ${item.remaining_amount} جنيه</strong>
        <form data-case="${item.id}" class="donationForm d-grid gap-2">
          <input type="number" class="form-control" min="1" placeholder="المبلغ" required>
          <select class="form-select paymentMethod" required>
            <option value="vodafone_cash">فودافون كاش</option>
            <option value="instapay">انستا باي</option>
            <option value="visa">فيزا</option>
          </select>
          <button class="btn btn-success">تبرع للحالة</button>
        </form>
      </div>`;
    list.appendChild(card);
  });

  document.querySelectorAll('.donationForm').forEach((form) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const amount = Number(form.querySelector('input').value);
      const paymentMethod = form.querySelector('.paymentMethod').value;
      const caseId = form.dataset.case;
      const res = await fetch(`/api/cases/${caseId}/donate`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, payment_method: paymentMethod }),
      });
      const data = await res.json();
      if (!res.ok) return alert(data.detail || 'فشل');
      alert(`${data.message}\nللمحتاج: ${data.beneficiary_share}\nللجمعية: ${data.organization_share}\nرقم الإيصال: ${data.receipt_code}`);
      loadCases();
    });
  });
}

document.getElementById('applyFilters')?.addEventListener('click', loadCases);

document.getElementById('directDonationForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const orgId = document.getElementById('directOrg').value;
  const amount = Number(document.getElementById('directAmount').value);
  const payment_method = document.getElementById('directPaymentMethod').value;
  const res = await fetch(`/api/donate/direct?organization_id=${orgId}`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ amount, payment_method }),
  });
  const data = await res.json();
  alert(data.message ? `${data.message}\nرقم الإيصال: ${data.receipt_code}` : (data.detail || 'فشل'));
});

async function loadAdmin() {
  if (!document.getElementById('orgChart')) return;
  const res = await fetch('/api/admin/dashboard', { headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) return;

  document.getElementById('totalDonations').textContent = `${data.total_donations} جنيه`;
  document.getElementById('donorsCount').textContent = data.donors_count;
  document.getElementById('beneficiariesCount').textContent = data.beneficiaries_count;
  document.getElementById('openCasesCount').textContent = data.open_cases_count;

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
