// ========================================
// Global Variables
// ========================================
let currentEvaluationData = null;
let provincesData = [];

// ========================================
// Document Ready
// ========================================
$(document).ready(function() {
    // โหลดข้อมูลจังหวัด
    loadProvinces();

    // ตรวจสอบสถานะ Ollama เมื่อเริ่มโหลดหน้า
    checkOllamaStatus();

    // ตั้งค่า Event Handlers
    setupEventHandlers();

    // ตรวจสอบ Ollama ทุก 30 วินาที
    setInterval(checkOllamaStatus, 30000);

    // File input change handler
    $('#excelFileInput').on('change', function() {
        const fileName = this.files[0] ? this.files[0].name : 'เลือกไฟล์ Excel หรือ CSV';
        $(this).siblings('.file-label').find('span').text(fileName);
    });
});

// ========================================
// Event Handlers Setup
// ========================================
function setupEventHandlers() {
    // Form Submit - Evaluation
    $('#evaluationForm').on('submit', function(e) {
        e.preventDefault();
        submitEvaluation();
    });

    // Form Submit - Quick Estimate
    $('#quickEstimateForm').on('submit', function(e) {
        e.preventDefault();
        submitQuickEstimate();
    });

    // Smooth Scroll for Navigation
    $('.nav-link').on('click', function(e) {
        e.preventDefault();
        const target = $(this).attr('href');
        $('html, body').animate({
            scrollTop: $(target).offset().top - 80
        }, 800);

        // Update active link
        $('.nav-link').removeClass('active');
        $(this).addClass('active');
    });
}

// ========================================
// Check Ollama Status
// ========================================
function checkOllamaStatus() {
    $.ajax({
        url: '/api/check-ollama',
        method: 'GET',
        success: function(response) {
            const $status = $('#ollamaStatus');
            if (response.connected) {
                $status.removeClass('disconnected checking')
                       .addClass('connected');
                $status.find('span').text('AI เชื่อมต่อแล้ว');

                // แสดง models ที่มี (ถ้ามี)
                if (response.models && response.models.length > 0) {
                    console.log('Available Ollama models:', response.models);
                }
            } else {
                $status.removeClass('connected checking')
                       .addClass('disconnected');
                $status.find('span').text('Ollama ไม่เชื่อมต่อ');
            }
        },
        error: function() {
            const $status = $('#ollamaStatus');
            $status.removeClass('connected checking')
                   .addClass('disconnected');
            $status.find('span').text('Ollama ไม่เชื่อมต่อ');
        }
    });
}

// ========================================
// Load Provinces Data
// ========================================
function loadProvinces() {
    $.ajax({
        url: '/api/provinces',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                provincesData = response.provinces;

                // สร้าง options สำหรับ dropdown
                let optionsHTML = '<option value="">เลือกจังหวัด</option>';

                // จัดกลุ่มตามภูมิภาค
                const regions = {
                    'กลาง': [],
                    'เหนือ': [],
                    'อีสาน': [],
                    'ใต้': []
                };

                // แยกจังหวัดตามภูมิภาค
                provincesData.forEach(function(province) {
                    regions[province.region].push(province);
                });

                // สร้าง optgroup สำหรับแต่ละภูมิภาค
                for (const region in regions) {
                    if (regions[region].length > 0) {
                        optionsHTML += `<optgroup label="ภาค${region}">`;
                        regions[region].forEach(function(province) {
                            optionsHTML += `<option value="${province.name}">${province.name}</option>`;
                        });
                        optionsHTML += '</optgroup>';
                    }
                }

                // อัปเดต dropdown ทั้งสอง
                $('#province').html(optionsHTML);
                $('#quickProvince').html(optionsHTML);

                console.log(`โหลดข้อมูล ${response.total} จังหวัดเรียบร้อยแล้ว`);
            } else {
                showNotification('ไม่สามารถโหลดข้อมูลจังหวัดได้', 'error');
            }
        },
        error: function() {
            showNotification('เกิดข้อผิดพลาดในการโหลดจังหวัด', 'error');
            // ใส่ค่า default ถ้า error
            $('#province').html('<option value="">ไม่สามารถโหลดจังหวัดได้</option>');
            $('#quickProvince').html('<option value="">ไม่สามารถโหลดจังหวัดได้</option>');
        }
    });
}

// ========================================
// Submit Evaluation (AI)
// ========================================
function submitEvaluation() {
    // ดึงข้อมูลจาก form
    const formData = {
        property_type: $('#propertyType').val(),
        location: $('#province').val(),
        area: $('#area').val(),
        bedrooms: $('#bedrooms').val(),
        bathrooms: $('#bathrooms').val(),
        age: $('#age').val(),
        condition: $('#condition').val(),
        additional_info: $('#additionalInfo').val()
    };

    // Validate
    if (!formData.property_type || !formData.location || !formData.area) {
        showNotification('กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน', 'warning');
        return;
    }

    // แสดง loading
    $('#evaluationForm').hide();
    $('#loading').show();

    // เก็บข้อมูลไว้ใช้ภายหลัง
    currentEvaluationData = formData;

    // เรียก API
    $.ajax({
        url: '/api/evaluate',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        timeout: 120000, // 2 minutes timeout
        success: function(response) {
            if (response.success) {
                displayResult(response);
                showNotification('ประเมินราคาสำเร็จ', 'success');
            } else {
                showError(response.error || 'เกิดข้อผิดพลาดในการประเมินราคา');
            }
        },
        error: function(xhr) {
            let errorMsg = 'ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMsg = xhr.responseJSON.error;
            }
            showError(errorMsg);
        },
        complete: function() {
            $('#loading').hide();
            $('#evaluationForm').show();
        }
    });
}

// ========================================
// Submit Quick Estimate
// ========================================
function submitQuickEstimate() {
    const formData = {
        property_type: $('#quickPropertyType').val(),
        area: $('#quickArea').val(),
        province: $('#quickProvince').val()
    };

    // Validate
    if (!formData.property_type || !formData.area || !formData.province) {
        showNotification('กรุณากรอกข้อมูลให้ครบถ้วน', 'warning');
        return;
    }

    // เรียก API
    $.ajax({
        url: '/api/quick-estimate',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                displayQuickResult(response);
            } else {
                showNotification(response.error || 'เกิดข้อผิดพลาด', 'error');
            }
        },
        error: function() {
            showNotification('ไม่สามารถคำนวณราคาได้', 'error');
        }
    });
}

// ========================================
// Display Result (AI Evaluation)
// ========================================
function displayResult(response) {
    const data = response.property_data;
    const evaluation = response.evaluation;

    // สร้าง HTML สำหรับสรุปข้อมูลทรัพย์สิน
    let summaryHTML = '<h4><i class="fas fa-home"></i> ข้อมูลทรัพย์สิน</h4>';
    summaryHTML += '<div class="property-info">';

    if (data.property_type) {
        summaryHTML += `
            <div class="property-info-item">
                <i class="fas fa-building"></i>
                <span><strong>ประเภท:</strong> ${data.property_type}</span>
            </div>
        `;
    }

    if (data.location) {
        summaryHTML += `
            <div class="property-info-item">
                <i class="fas fa-map-marker-alt"></i>
                <span><strong>ทำเล:</strong> ${data.location}</span>
            </div>
        `;
    }

    if (data.area) {
        summaryHTML += `
            <div class="property-info-item">
                <i class="fas fa-ruler-combined"></i>
                <span><strong>ขนาด:</strong> ${data.area} ตร.ม.</span>
            </div>
        `;
    }

    if (data.bedrooms) {
        summaryHTML += `
            <div class="property-info-item">
                <i class="fas fa-bed"></i>
                <span><strong>ห้องนอน:</strong> ${data.bedrooms} ห้อง</span>
            </div>
        `;
    }

    if (data.bathrooms) {
        summaryHTML += `
            <div class="property-info-item">
                <i class="fas fa-bath"></i>
                <span><strong>ห้องน้ำ:</strong> ${data.bathrooms} ห้อง</span>
            </div>
        `;
    }

    if (data.age) {
        summaryHTML += `
            <div class="property-info-item">
                <i class="fas fa-calendar-alt"></i>
                <span><strong>อายุ:</strong> ${data.age} ปี</span>
            </div>
        `;
    }

    summaryHTML += '</div>';

    // แสดงผลลัพธ์
    $('#propertySummary').html(summaryHTML);
    $('#resultContent').html(formatEvaluation(evaluation));
    $('#resultCard').fadeIn(500);

    // Scroll to result
    $('html, body').animate({
        scrollTop: $('#resultCard').offset().top - 100
    }, 800);
}

// ========================================
// Format Evaluation Text
// ========================================
function formatEvaluation(text) {
    // แปลง text ให้อ่านง่ายขึ้น
    let formatted = text.replace(/\n/g, '<br>');

    // เน้นข้อความที่สำคัญ
    formatted = formatted.replace(/(\d+[\d,]*\s*บาท)/g, '<strong style="color: var(--primary-color); font-size: 1.1em;">$1</strong>');
    formatted = formatted.replace(/(ราคาประเมิน|ราคาโดยประมาณ)/gi, '<strong style="color: var(--success-color);">$1</strong>');

    return formatted;
}

// ========================================
// Display Quick Result
// ========================================
function displayQuickResult(response) {
    const price = response.estimated_price;
    const pricePerSqm = response.price_per_sqm;
    const area = response.area;

    // Format ราคา
    const formattedPrice = price.toLocaleString('th-TH', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });

    const formattedPricePerSqm = pricePerSqm.toLocaleString('th-TH', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });

    let detailText = `${formattedPricePerSqm} บาท/ตร.ม. × ${area} ตร.ม.`;
    if (response.province) {
        detailText += ` | ${response.province}`;
    }
    if (response.region) {
        detailText += ` (ภาค${response.region})`;
    }

    $('#quickPrice').text(formattedPrice + ' บาท');
    $('#quickDetail').text(detailText);
    $('#quickResult').fadeIn(500);
}

// ========================================
// Show Notification
// ========================================
function showNotification(message, type = 'info') {
    // สร้าง notification element
    const colors = {
        success: 'var(--success-color)',
        warning: 'var(--warning-color)',
        error: 'var(--danger-color)',
        info: 'var(--primary-color)'
    };

    const icons = {
        success: 'fa-check-circle',
        warning: 'fa-exclamation-triangle',
        error: 'fa-times-circle',
        info: 'fa-info-circle'
    };

    const $notification = $(`
        <div class="notification" style="
            position: fixed;
            top: 100px;
            right: 20px;
            background: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            border-left: 4px solid ${colors[type]};
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            animation: slideInRight 0.3s ease;
            min-width: 300px;
        ">
            <i class="fas ${icons[type]}" style="color: ${colors[type]}; font-size: 1.25rem;"></i>
            <span style="flex: 1;">${message}</span>
            <button onclick="$(this).parent().fadeOut(300, function() { $(this).remove(); })"
                style="background: none; border: none; cursor: pointer; font-size: 1.25rem; color: var(--gray-color);">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `);

    $('body').append($notification);

    // Auto remove after 5 seconds
    setTimeout(function() {
        $notification.fadeOut(300, function() {
            $(this).remove();
        });
    }, 5000);
}

// ========================================
// Show Error
// ========================================
function showError(message) {
    showNotification(message, 'error');

    // ถ้าเป็นปัญหาการเชื่อมต่อ Ollama ให้แสดงคำแนะนำ
    if (message.includes('Ollama')) {
        setTimeout(function() {
            showNotification('กรุณาตรวจสอบว่า Ollama กำลังทำงานที่ http://localhost:11434', 'info');
        }, 500);
    }
}

// ========================================
// Helper Functions
// ========================================
function scrollToEvaluate() {
    $('html, body').animate({
        scrollTop: $('#evaluate').offset().top - 80
    }, 800);
}

function showQuickEstimate() {
    $('#quickEstimateModal').addClass('active');
}

function closeQuickEstimate() {
    $('#quickEstimateModal').removeClass('active');
    $('#quickResult').hide();
    $('#quickEstimateForm')[0].reset();
}

function closeResult() {
    $('#resultCard').fadeOut(300);
}

function resetForm() {
    $('#evaluationForm')[0].reset();
    $('#resultCard').fadeOut(300);
    currentEvaluationData = null;
}

function downloadPDF() {
    if (!currentEvaluationData) {
        showNotification('ไม่มีข้อมูลการประเมิน', 'warning');
        return;
    }

    // แสดงข้อความกำลังสร้าง PDF
    showNotification('กำลังสร้าง PDF...', 'info');

    // ดึงข้อมูลจาก result card
    const evaluationText = $('#resultContent').text();

    // เรียก API เพื่อสร้าง PDF
    fetch('/api/download-pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            property_data: currentEvaluationData,
            evaluation: evaluationText
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('ไม่สามารถสร้าง PDF ได้');
        }
        return response.blob();
    })
    .then(blob => {
        // สร้าง URL สำหรับ blob
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `property_evaluation_${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showNotification('ดาวน์โหลด PDF สำเร็จ', 'success');
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('เกิดข้อผิดพลาดในการดาวน์โหลด PDF', 'error');
    });
}

function shareResult() {
    if (navigator.share && currentEvaluationData) {
        navigator.share({
            title: 'ผลการประเมินราคาทรัพย์สิน - มั่นใจ',
            text: `ประเมินราคา${currentEvaluationData.property_type}ที่${currentEvaluationData.location}`,
            url: window.location.href
        }).catch(err => {
            console.log('Error sharing:', err);
            copyToClipboard();
        });
    } else {
        copyToClipboard();
    }
}

function copyToClipboard() {
    const url = window.location.href;
    const tempInput = $('<input>');
    $('body').append(tempInput);
    tempInput.val(url).select();
    document.execCommand('copy');
    tempInput.remove();

    showNotification('คัดลอก URL แล้ว', 'success');
}

// ========================================
// Excel Upload Functions
// ========================================
function uploadExcelFile() {
    const fileInput = document.getElementById('excelFileInput');
    const file = fileInput.files[0];

    if (!file) {
        showNotification('กรุณาเลือกไฟล์', 'warning');
        return;
    }

    // ตรวจสอบนามสกุลไฟล์
    const allowedExtensions = ['xlsx', 'xls', 'csv'];
    const fileExtension = file.name.split('.').pop().toLowerCase();

    if (!allowedExtensions.includes(fileExtension)) {
        showNotification('รองรับเฉพาะไฟล์ .xlsx, .xls, .csv เท่านั้น', 'error');
        return;
    }

    // แสดงสถานะกำลังอัปโหลด
    showNotification('กำลังอัปโหลดไฟล์...', 'info');

    // สร้าง FormData
    const formData = new FormData();
    formData.append('file', file);

    // อัปโหลดไฟล์
    fetch('/api/upload-price-data', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(
                `${data.message} (รวม ${data.total_records} รายการ)`,
                'success'
            );

            // แสดง errors ถ้ามี
            if (data.errors && data.errors.length > 0) {
                console.warn('Upload errors:', data.errors);
                showNotification(
                    `มี ${data.error_count} รายการที่ไม่สามารถอัปโหลดได้`,
                    'warning'
                );
            }

            // ล้างไฟล์ที่เลือก
            fileInput.value = '';

            // ปิด modal
            closeUploadModal();
        } else {
            showNotification(data.error || 'เกิดข้อผิดพลาดในการอัปโหลด', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('เกิดข้อผิดพลาดในการอัปโหลด', 'error');
    });
}

function downloadTemplate() {
    showNotification('กำลังดาวน์โหลด template...', 'info');

    fetch('/api/download-template')
    .then(response => {
        if (!response.ok) {
            throw new Error('ไม่สามารถดาวน์โหลดได้');
        }
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'price_data_template.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showNotification('ดาวน์โหลด template สำเร็จ', 'success');
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('เกิดข้อผิดพลาดในการดาวน์โหลด', 'error');
    });
}

function showUploadModal() {
    $('#uploadModal').addClass('active');
}

function closeUploadModal() {
    $('#uploadModal').removeClass('active');
    $('#excelFileInput').val('');
}

// ========================================
// Close Modal on Outside Click
// ========================================
$(document).on('click', '.modal', function(e) {
    if ($(e.target).hasClass('modal')) {
        $(this).removeClass('active');
    }
});

// ========================================
// Escape Key to Close Modals
// ========================================
$(document).on('keydown', function(e) {
    if (e.key === 'Escape') {
        $('.modal').removeClass('active');
        closeResult();
    }
});
