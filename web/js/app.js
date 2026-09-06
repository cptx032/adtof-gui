(function () {
  const maxBytes = 50 * 1024 * 1024;
  const audioExtensions = [
    "aac",
    "aif",
    "aiff",
    "flac",
    "m4a",
    "mp3",
    "mpga",
    "oga",
    "ogg",
    "opus",
    "wav",
    "wma",
  ];
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const btnSelect = document.getElementById("btnSelect");
  const btnConvert = document.getElementById("btnConvert");
  const fileName = document.getElementById("fileName");
  const convertStatus = document.getElementById("convertStatus");

  /** @type {File | null} */
  let selectedFile = null;

  /**
   * @param {string} message
   * @returns {void}
   */
  function setStatus(message) {
    convertStatus.textContent = message;
  }

  /**
   * @param {string} name
   * @returns {string}
   */
  function fileExtension(name) {
    const dot = name.lastIndexOf(".");
    if (dot < 0) {
      return "";
    }
    return name.slice(dot + 1).toLowerCase();
  }

  /**
   * @param {File} file
   * @returns {boolean}
   */
  function isSupportedAudio(file) {
    return audioExtensions.indexOf(fileExtension(file.name)) !== -1;
  }

  /**
   * @param {string} name
   * @returns {string}
   */
  function fileStem(name) {
    const ext = fileExtension(name);
    if (!ext) {
      return name || "drums";
    }
    return name.slice(0, name.length - ext.length - 1) || "drums";
  }

  /**
   * @param {File | undefined} file
   * @returns {void}
   */
  function applyFile(file) {
    if (!file) {
      return;
    }
    if (!isSupportedAudio(file)) {
      selectedFile = null;
      fileName.hidden = true;
      btnConvert.disabled = true;
      setStatus("Envie um arquivo de áudio suportado.");
      return;
    }
    if (file.size > maxBytes) {
      selectedFile = null;
      fileName.hidden = true;
      btnConvert.disabled = true;
      setStatus("O arquivo ultrapassa 50MB.");
      return;
    }
    selectedFile = file;
    fileName.hidden = false;
    fileName.textContent = file.name;
    btnConvert.disabled = false;
    setStatus("");
  }

  /**
   * @returns {void}
   */
  function openPicker() {
    fileInput.click();
  }

  dropzone.addEventListener("click", function (event) {
    const target = event.target;
    if (target instanceof HTMLElement && target.closest("#btnSelect")) {
      return;
    }
    openPicker();
  });

  dropzone.addEventListener("keydown", function (event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openPicker();
    }
  });

  btnSelect.addEventListener("click", function (event) {
    event.stopPropagation();
    openPicker();
  });

  fileInput.addEventListener("change", function () {
    const files = fileInput.files;
    applyFile(files && files[0] ? files[0] : undefined);
  });

  ["dragenter", "dragover"].forEach(function (type) {
    dropzone.addEventListener(type, function (event) {
      event.preventDefault();
      dropzone.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach(function (type) {
    dropzone.addEventListener(type, function (event) {
      event.preventDefault();
      dropzone.classList.remove("is-dragover");
    });
  });

  dropzone.addEventListener("drop", function (event) {
    const files = event.dataTransfer ? event.dataTransfer.files : null;
    applyFile(files && files[0] ? files[0] : undefined);
  });

  /**
   * @param {File} file
   * @returns {Promise<void>}
   */
  async function convertFile(file) {
    btnConvert.disabled = true;
    setStatus("Transcrevendo...");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch("/api/convert", {
        method: "POST",
        body: body,
      });
      const contentType = response.headers.get("content-type") || "";
      if (!response.ok) {
        if (contentType.indexOf("application/json") !== -1) {
          const data = await response.json();
          setStatus(data.message || "Não foi possível transcrever o áudio.");
        } else {
          setStatus("Não foi possível transcrever o áudio.");
        }
        btnConvert.disabled = false;
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const stem = fileStem(file.name);
      link.href = url;
      link.download = stem + ".mid";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setStatus("MIDI pronto.");
    } catch (_error) {
      setStatus("Não foi possível transcrever o áudio.");
    }
    btnConvert.disabled = false;
  }

  btnConvert.addEventListener("click", function () {
    if (!selectedFile) {
      setStatus("Selecione um arquivo de áudio.");
      return;
    }
    convertFile(selectedFile);
  });
})();
