# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Create a new data table and populate its rows using the contents of a file.

API reference:
https://cloud.google.com/chronicle/docs/reference/rest/v1alpha/projects.locations.instances.dataTables/upload
"""

import json
import logging
import os
import pathlib
import time
from typing import Any, Mapping, Sequence

from google.auth.transport import requests

LOGGER = logging.getLogger()


def upload_data_table(
    http_session: requests.AuthorizedSession,
    name: str,
    description: str,
    column_info: Sequence[Mapping[str, Any]],
    file_path: pathlib.Path,
    row_time_to_live: str | None = None,
    max_retries: int = 3,
) -> Mapping[str, Any]:
  """Creates a new data table and populates its rows using the contents of a file.

  Args:
    http_session: Authorized session for HTTP requests.
    name: The unique ID to use for the new data table. This is also the display
      name for the data table. It must satisfy the following requirements -
      Starts with a letter. - Contains only letters, numbers and underscore
      characters. - Must be unique and has length < 256.
    description: A user-provided description of the data table.
    column_info: Details of the columns for the data table. reference -
      https://cloud.google.com/chronicle/docs/reference/rest/Shared.Types/BulkDataTableAsync#DataTableColumnInfo
    file_path: The path to the file that will be used to populate the rows of
      the data table.
    row_time_to_live (optional): Time to Live (TTL) for rows in the data table.
      (e.g. 24h, 48h, 3d). A row is deleted when its expiration time is reached.
      Minimum allowed value: 24h, Maximum allowed value: 365d.
    max_retries (optional): Maximum number of times to retry HTTP request if
      certain response codes are returned. For example: HTTP response status
      code 429 (Too Many Requests)

  Returns:
    An Operation that can be monitored for completion. Reference -
      https://cloud.google.com/chronicle/docs/reference/rest/Shared.Types/ListOperationsResponse#Operation

  Raises:
    requests.exceptions.HTTPError: HTTP request resulted in an error
    (response.status_code >= 400).
    requests.exceptions.JSONDecodeError: If the server response is not valid
    JSON.
  """
  url = f"{os.environ['GOOGLE_SECOPS_API_UPLOAD_BASE_URL']}/{os.environ['GOOGLE_SECOPS_INSTANCE']}/dataTables:bulkCreateDataTableAsync"
  data_table_metadata = {
      "data_table_id": name,
      "data_table": {
          "name": f"{os.environ['GOOGLE_SECOPS_INSTANCE']}/dataTables/{name}",
          "description": description,
          "column_info": column_info,
          "row_time_to_live": row_time_to_live,
      },
  }
  headers = {
      "X-Return-Encrypted-Headers": "all_response",
      "X-Goog-Upload-Protocol": "multipart",
  }

  response = None

  for _ in range(max(max_retries, 0) + 1):
    # Open a handle to the file that will be uploaded
    with open(file_path, "rb") as f:
      files = {"file": f}
      data = {"data_table": json.dumps(data_table_metadata)}

      response = http_session.request(
          method="POST", url=url, headers=headers, data=data, files=files
      )

    if response.status_code >= 400:
      LOGGER.warning(response.text)

    if response.status_code == 429:
      LOGGER.warning(
          "API rate limit exceeded. Sleeping for 60s before retrying"
      )
      time.sleep(60)
    else:
      break

  response.raise_for_status()

  response_json = response.json()

  LOGGER.info("Operation: %s", json.dumps(response_json, indent=4))

  return response_json
