import mimetypes
import os

import frappe
from frappe import _
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.wrappers import Response


@frappe.whitelist()
def create_drive_file(name: str, parent: str | None = None, title: str | None = "Untitled") -> str:
	"""
	Creates a corresponding Drive File for a Slides Presentation.
	"""
	from drive.utils import create_file

	file = create_file(
		title=title,
		parent=parent,
		mime_type="frappe/slides",
		file_type="Presentation",
		content_doctype="Presentation",
		content_docname=name,
	)
	return file.name


def get_file_size(file_path: str) -> int:
	"""
	Returns the size of the file at the given path.
	"""
	return os.path.getsize(file_path)


def get_range(range_header: str, file_size: int) -> tuple[int, int]:
	"""
	Extracts the byte range from Range header.
	"""
	import re

	range_start, range_end = 0, None
	match = re.search(r"bytes=(\d+)-(\d*)", range_header)

	if match:
		range_start = int(match.group(1))
		if match.group(2):
			range_end = int(match.group(2))

	range_end = range_end or file_size - 1

	return range_start, range_end


def get_file_data(file_path: str, range_start: int = 0, range_end: int = 0) -> bytes:
	"""
	Returns specified range of bytes from the file.
	If range_end is None, returns the full file content.
	"""
	with open(file_path, "rb") as f:
		f.seek(range_start)

		if range_end == 0:
			# return the full file content in the response
			data = f.read()
		else:
			# read the specified range from the file
			data = f.read(range_end - range_start + 1)

	return data


def get_file_metadata(src: str) -> tuple[str, int, str]:
	"""
	Returns file metadata including path, size, and MIME type.
	"""
	if src.startswith("/files"):
		src = "/public" + src
	file_path = frappe.get_site_path() + src
	file_size = get_file_size(file_path)
	mimetype = mimetypes.guess_type(file_path)[0] or "video/mp4"

	return file_path, file_size, mimetype


def get_media_response(src: str) -> Response:
	"""
	Processes the range header from browser to return valid response.
	"""
	file_path, file_size, mimetype = get_file_metadata(src)

	range_header = frappe.request.headers.get("Range", None)
	range_start, range_end = None, None

	# if the request includes a Range header, return a partial content response
	if range_header:
		range_start, range_end = get_range(range_header, file_size)

		file_data = get_file_data(file_path, range_start, range_end)
		status_code = 206  # Partial Content
		content_length = range_end - range_start + 1

	# otherwise, return the full content response
	else:
		file_data = get_file_data(file_path)
		status_code = 200  # Full Content
		content_length = file_size

	response = Response(file_data, status_code, mimetype=mimetype, direct_passthrough=True)
	response.headers["Content-Length"] = str(content_length)
	response.headers["Accept-Ranges"] = "bytes"

	if range_start is not None and range_end is not None:
		response.headers["Content-Range"] = f"bytes {range_start}-{range_end}/{file_size}"
	return response


def validate_media_file(src, public) -> None:
	# check for existence and permissions of the file
	file_doc = frappe.get_doc("File", {"file_url": src})

	if not file_doc:
		raise NotFound

	# check if the user has read permission on the file
	if not public and not frappe.has_permission("File", "read", file_doc):
		raise Forbidden(_("You don't have permission to access this file"))


@frappe.whitelist(allow_guest=True)
def get_media_file(src: str, public: str) -> Response:
	"""
	Fetches permitted video file and returns a response.
	"""
	validate_media_file(src, public)

	return get_media_response(src)
