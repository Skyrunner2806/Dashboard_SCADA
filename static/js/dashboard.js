document.addEventListener("DOMContentLoaded", function () {
    const contaminationInput = document.querySelector("input[name='contamination']");
    if (contaminationInput) {
        contaminationInput.addEventListener("input", function () {
            const url = new URL(window.location);
            const contamination = contaminationInput.value;
            url.searchParams.set("contamination", contamination);
            window.location.href = url.toString();
        });
    }
});
