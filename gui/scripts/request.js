
/**
 * Gets a file's info.
 * @param  {int}       id the ID of the file to get.
 * @return {Document}     A list of file data (not all data is loaded).
 */
async function getFileInfo(id) {
  const ret = await eel.get_file_info(id)();
  if(ret) eel.open_file(id);
  return ret;
}

async function getFiles() {
  return await eel.get_files()();
}

/**
 * Fetches info about a scene.
 * @param  {int}   scene The scene number.
 * @return {Scene}
 */
async function getSceneInfo(scene) {
  return await eel.get_scene_info(scene)();
}

async function changeSceneInfo(scene, scriptIndex, newScript) {
  return await eel.change_scene_info(scene, scriptIndex, newScript)();
}

async function deleteScriptPart(scene, scriptIndex) {
  return await eel.delete_script_part(scene, scriptIndex)();
}

async function deleteScene(sceneIndex) {
  return await eel.delete_scene(++sceneIndex)();
}

/**
 * Changes scenes elements from startI to endI.
 * @param  {int} startI The start index.
 * @param  {int} endI   The end index.
 */
async function relocateItem(startI, endI) {
  await eel.relocate_scene(++startI, ++endI);
}

/**
 * Opens a file prompt and asks for an .mp3 file.
 * @return { Soundtrack } null if no soundtrack or an invalid file was selected.
 */
async function getSoundtrackFromFile(number, callback) {
  let input = document.createElement("input");
  input.type = "file";
  input.accept = ".mp3";
  input.addEventListener("change", async evtInput => {
    const file = evtInput.target.files[0];
    const reader = new FileReader();
    reader.addEventListener('load', async evtReader => {
      const songBin = evtReader.target.result;
      let fileName = evtReader.target.fileName || file.name;
      const song = await eel.set_song(number, fileName, songBin)();
      if(song)
        callback(song);
    });
    reader.readAsDataURL(file);
  })
  input.click();
}

/**
 * Opens a file prompt and asks for an image.
 * @param  {int}    scene The scene number the image is for.
 * @return {string}       The selected image, encoded in b64.
 */
async function getImageFromFile(scene, onSelect) {
  let input = document.createElement("input");
  input.type = "file";
  input.accept = ".jpg, .jpeg, .png";
  input.addEventListener("change", async evtInput => {
    const file = evtInput.target.files[0];
    const reader = new FileReader();
    reader.addEventListener('load', async evtReader => {
      const image = evtReader.target.result;
      const success = await eel.set_image(scene, image)()
      if(success)
        onSelect(image);
    });
    reader.readAsDataURL(file);
  })
  input.click();
}

/**
 * [addToScript description]
 * @param  {("transition" | "soundtrack" | "scene")[]} scenes List of parts to add.
 * @param  {int}                                       index  The index to add the parts on. Default: last
 * @return {Scene[]}                                          The newly created scenes.
 */
async function addToScript(types, index=null) {
  const ret = await eel.add_to_script(types)()
  return ret
}

/**
 * Creates a new file with basic settings.
 * @param  {string}   name The name of the new file.
 * @return {Document}      The newly created file.
 */
async function createFile(name) {
  const ret = await eel.create_file(name)()
  eel.open_file(ret.id)
  return ret
}

/**
 * Deletes a file.
 * @param  {int} id  The ID of the file to delete.
 */
async function deleteFile(id) {
  await eel.delete_file(id)
}

async function exportFile(callback) {
  actualGuiCallback = callback;
  await eel.export_file();
}

eel.expose(gui_callback);
let actualGuiCallback = () => null;
function gui_callback(evt) {
  actualGuiCallback(evt)
}

async function downloadImages(platform, target, platformSpecific, callback) {
  const zipFile = await eel.download_images(platform, target, platformSpecific)(callback);
}

async function loadVideoDuration() {
  return await eel.load_video_duration()();
}

async function detectText(scene, crop) {
  return await eel.detect_text(scene, crop)();
}
